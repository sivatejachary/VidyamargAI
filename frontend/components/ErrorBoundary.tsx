"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./ui/Button";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error inside ErrorBoundary:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-6 text-center border border-border/50 bg-card/10 backdrop-blur-md rounded-3xl max-w-lg mx-auto my-12 shadow-lg">
          <div className="p-4 rounded-full bg-destructive/10 text-destructive mb-4">
            <AlertTriangle size={32} />
          </div>
          <h2 className="text-xl font-extrabold text-foreground mb-2">Something went wrong</h2>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm leading-relaxed">
            An unexpected error occurred in this application section. If this problem persists, please contact support.
          </p>
          {this.state.error && (
            <pre className="text-left w-full p-4 mb-6 text-xs bg-muted/50 rounded-xl overflow-x-auto text-muted-foreground border border-border/40 max-h-40 overflow-y-auto">
              <code>{this.state.error.toString()}</code>
            </pre>
          )}
          <Button
            onClick={this.handleReset}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw size={16} />
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
