import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Predefined recommendations mapping for popular tech skills
REC_MAP = {
    "docker": {
        "certs": ["Docker Certified Associate (DCA)"],
        "projects": ["Containerize a Django/FastAPI app with PostgreSQL using Docker Compose"],
        "roadmap": "Learn Docker basics (Images, Containers, Volumes, Networking) -> Practice writing Dockerfiles -> Learn Docker Compose."
    },
    "kubernetes": {
        "certs": ["Certified Kubernetes Application Developer (CKAD)"],
        "projects": ["Deploy a microservices cluster on Kubernetes using Minikube"],
        "roadmap": "Understand Pods, Deployments, Services, and ConfigMaps -> Set up a local cluster -> Deploy multi-container apps."
    },
    "aws": {
        "certs": ["AWS Certified Cloud Practitioner", "AWS Certified Solutions Architect - Associate"],
        "projects": ["Deploy a serverless backend with AWS Lambda, API Gateway, and DynamoDB"],
        "roadmap": "Learn Core Services (EC2, S3, RDS, IAM) -> Understand Serverless -> Practice VPC & Security Groups."
    },
    "fastapi": {
        "certs": ["Python Web Developer Certification"],
        "projects": ["Build a real-time chat API with FastAPI WebSockets and Redis caching"],
        "roadmap": "Learn asynchronous Python -> Build REST endpoints with Pydantic validations -> Implement JWT authentication."
    },
    "react": {
        "certs": ["Meta Front-End Developer Certificate"],
        "projects": ["Create a drag-and-drop Kanban board with React and Tailwind CSS"],
        "roadmap": "Learn React state & effects -> Master component lifecycle & custom hooks -> Learn state management (Redux/Zustand)."
    },
    "next.js": {
        "certs": ["Vercel Next.js Developer Certificate"],
        "projects": ["Build an SEO-optimized E-commerce storefront with Server Components"],
        "roadmap": "Understand Server vs Client components -> Learn App Router navigation -> Implement Server Actions for data mutations."
    },
    "machine learning": {
        "certs": ["Google Cloud Professional ML Engineer", "Andrew Ng Machine Learning Specialization"],
        "projects": ["Train and deploy a customer churn prediction model using Scikit-Learn"],
        "roadmap": "Master Python data libraries (Pandas, NumPy) -> Learn regression & classification -> Practice hyperparameter tuning."
    },
    "pytorch": {
        "certs": ["Deep Learning Specialization"],
        "projects": ["Build and train a custom CNN for image recognition in PyTorch"],
        "roadmap": "Learn PyTorch tensors -> Build simple feedforward neural networks -> Understand Autograd and optimizers."
    },
    "tensorflow": {
        "certs": ["TensorFlow Developer Certificate"],
        "projects": ["Implement an NLP sentiment analysis model using TensorFlow Keras"],
        "roadmap": "Learn Keras API -> Master transfer learning -> Understand recurrent neural networks (RNNs) and Transformers."
    },
    "sql": {
        "certs": ["Microsoft Certified: Database Administrator Associate"],
        "projects": ["Design a relational schema for a multi-vendor marketplace database"],
        "roadmap": "Learn basic SELECT & JOIN operations -> Practice aggregate functions & GROUP BY -> Master window functions & indexing."
    }
}

class RecommendationAgent:
    def __init__(self, skill_gaps: List[Dict[str, Any]]):
        self.skill_gaps = skill_gaps

    def generate_recommendations(self) -> Dict[str, Any]:
        """
        Generates tailored certifications, projects, and learning roadmaps
        to bridge the identified candidate skill gaps.
        """
        recommended_skills = []
        recommended_certs = []
        recommended_projects = []
        roadmap_steps = []

        # Focus on High and Medium priority skill gaps
        target_gaps = [g for g in self.skill_gaps if g["priority"] in ["High", "Medium"]]
        
        # If no gaps, candidate matches perfectly! Generate stretch goals from skills
        if not target_gaps:
            target_gaps = self.skill_gaps[:2] if self.skill_gaps else []

        for gap in target_gaps:
            skill = gap["skill"]
            recommended_skills.append(skill)
            
            skill_key = skill.lower().strip()
            if skill_key in REC_MAP:
                mapping = REC_MAP[skill_key]
                recommended_certs.extend(mapping["certs"])
                recommended_projects.extend(mapping["projects"])
                roadmap_steps.append(f"For {skill}: {mapping['roadmap']}")
            else:
                # General default recommendation
                recommended_certs.append(f"Professional Certificate in {skill}")
                recommended_projects.append(f"Build a portfolio project demonstrating {skill} integration")
                roadmap_steps.append(f"For {skill}: Learn core concepts -> Build 2 mini-projects -> Share on GitHub.")

        # If we got no projects/certs, add general fallbacks
        if not recommended_certs:
            recommended_certs = ["AWS Cloud Practitioner", "Docker Certified Associate"]
        if not recommended_projects:
            recommended_projects = ["Build an autonomous full-stack portfolio app integrating AI APIs"]
        if not roadmap_steps:
            roadmap_steps = ["Identify your target role -> Learn core programming -> Learn git & DevOps basics."]

        return {
            "skills": recommended_skills[:5],
            "certifications": list(set(recommended_certs))[:3],
            "projects": list(set(recommended_projects))[:3],
            "roadmap": roadmap_steps[:3]
        }
