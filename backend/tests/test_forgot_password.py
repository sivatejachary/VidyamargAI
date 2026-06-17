import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.models import User, OTP, EmailNotification, Candidate
from app.core.security import verify_password

from sqlalchemy.pool import StaticPool

# Use sqlite in-memory database for fast testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestForgotPassword(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def setUp(self):
        # Clean up database tables for each test
        self.db = TestingSessionLocal()
        self.db.query(OTP).delete()
        self.db.query(EmailNotification).delete()
        self.db.query(Candidate).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Create a test candidate user
        self.test_email = "test_candidate@example.com"
        self.test_password = "OldPassword123!"
        from app.core.security import get_password_hash
        hashed_pwd = get_password_hash(self.test_password)
        
        self.user = User(
            email=self.test_email,
            password_hash=hashed_pwd,
            full_name="Test Candidate",
            role="candidate"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.candidate = Candidate(
            id=self.user.id,
            user_id=self.user.id
        )
        self.db.add(self.candidate)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_forgot_password_unregistered_email(self):
        # 1. User enters unregistered email address
        response = self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Email not registered", response.json()["detail"])

    def test_forgot_password_success_otp_generation(self):
        # 2. User enters registered email address -> OTP generated & stored
        response = self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self.test_email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"],
            "A verification code has been sent to your registered email address."
        )

        # Confirm OTP is not displayed/returned in API response
        self.assertNotIn("otp", response.json())
        self.assertNotIn("code", response.json())

        # Check database: OTP record exists
        otp_entry = self.db.query(OTP).filter(OTP.email == self.test_email).first()
        self.assertIsNotNone(otp_entry)
        self.assertEqual(len(otp_entry.otp), 6)
        self.assertTrue(otp_entry.otp.isdigit())
        self.assertFalse(otp_entry.used)
        
        # Check expiry is roughly 10 minutes from now
        now = datetime.utcnow()
        self.assertTrue(otp_entry.expiry_time > now)
        self.assertTrue(otp_entry.expiry_time <= now + timedelta(minutes=10.5))

        # Check EmailNotification is created as an in-app fallback log for verification
        notif = self.db.query(EmailNotification).filter(
            EmailNotification.recipient == self.test_email
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Password Reset Verification Code", notif.subject)
        self.assertIn(otp_entry.otp, notif.body)

    def test_forgot_password_rate_limiting(self):
        # 3. Add rate limiting: max 3 OTP requests per 15 minutes per email.
        for i in range(3):
            res = self.client.post(
                "/api/v1/auth/forgot-password",
                json={"email": self.test_email}
            )
            self.assertEqual(res.status_code, 200)

        # 4th request within 15 minutes should be rate limited (429)
        res = self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self.test_email}
        )
        self.assertEqual(res.status_code, 429)
        self.assertIn("Rate limit exceeded", res.json()["detail"])

    def test_reset_password_success(self):
        # Generate OTP
        self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self.test_email}
        )
        otp_entry = self.db.query(OTP).filter(OTP.email == self.test_email).first()
        code = otp_entry.otp

        # Reset password
        new_pwd = "NewSecurePassword456!"
        response = self.client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": self.test_email,
                "code": code,
                "new_password": new_pwd
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password updated successfully")

        # Mark OTP as used after successful reset
        self.db.refresh(otp_entry)
        self.assertTrue(otp_entry.used)

        # Verify password is hashed using bcrypt
        self.db.refresh(self.user)
        self.assertTrue(verify_password(new_pwd, self.user.password_hash))

    def test_reset_password_invalid_code(self):
        # Generate OTP
        self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self.test_email}
        )

        # Attempt reset with wrong code
        response = self.client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": self.test_email,
                "code": "000000",
                "new_password": "NewSecurePassword456!"
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid or expired verification code", response.json()["detail"])

    def test_reset_password_expired_code(self):
        # Manually insert an expired OTP
        expired_time = datetime.utcnow() - timedelta(minutes=1)
        otp_entry = OTP(
            email=self.test_email,
            otp="999999",
            expiry_time=expired_time,
            used=False
        )
        self.db.add(otp_entry)
        self.db.commit()

        # Attempt reset with expired code
        response = self.client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": self.test_email,
                "code": "999999",
                "new_password": "NewSecurePassword456!"
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid or expired verification code", response.json()["detail"])

        # Check that it automatically gets deleted in cleanup
        self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self.test_email}
        )
        count = self.db.query(OTP).filter(OTP.otp == "999999").count()
        self.assertEqual(count, 0)
