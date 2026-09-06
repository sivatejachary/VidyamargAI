import { Request, Response, NextFunction } from "express";

export interface AppError extends Error {
  statusCode?: number;
  detail?: string;
}

export const errorHandler = (
  err: AppError,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const status = err.statusCode || 500;
  const message = err.detail || err.message || "Internal Server Error";

  console.error(`[Error ${status}] ${req.method} ${req.originalUrl}:`, err.stack || err.message);

  res.status(status).json({
    detail: message,
    timestamp: new Date().toISOString(),
    path: req.originalUrl,
  });
};
