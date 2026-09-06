import { Request, Response, NextFunction } from "express";
import * as jose from "jose";
import { env } from "../config/env.js";
import { query } from "../database/pool.js";

export interface AuthenticatedUser {
  id: number;
  email: string;
  role: string;
  full_name?: string;
}

declare global {
  namespace Express {
    interface Request {
      user?: AuthenticatedUser;
    }
  }
}

export const authenticateJwt = async (
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    res.status(401).json({ detail: "Could not validate credentials" });
    return;
  }

  const token = authHeader.split(" ")[1];
  try {
    const secret = new TextEncoder().encode(env.JWT_SECRET);
    const { payload } = await jose.jwtVerify(token, secret);
    const email = payload.sub as string;

    if (!email) {
      res.status(401).json({ detail: "Could not validate credentials" });
      return;
    }

    const result = await query("SELECT id, email, role, full_name FROM users WHERE email = $1", [email]);
    const user = result.rows[0];

    if (!user) {
      res.status(401).json({ detail: "User not found or credentials expired" });
      return;
    }

    req.user = user;
    next();
  } catch (err) {
    res.status(401).json({ detail: "Could not validate credentials" });
  }
};

export const requireAdmin = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  if (!req.user || !["admin", "super_admin"].includes(req.user.role)) {
    res.status(403).json({ detail: "The user does not have enough privileges" });
    return;
  }
  next();
};
