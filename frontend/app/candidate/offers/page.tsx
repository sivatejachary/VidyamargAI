"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { Award, FileText, CheckCircle2, ChevronRight, Mail, Sparkles, Building, UserCheck } from "lucide-react";

export default function CandidateOffers() {
  const [apps, setApps] = useState<any[]>([]);
  const [selectedApp, setSelectedApp] = useState<any>(null);
  const [offer, setOffer] = useState<any>(null);
  
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const fetchData = async () => {
    try {
      const data = await apiService.getApplications();
      // Applications with offers or active onboarding
      const offerApps = data.filter((a: any) => 
        a.status.toLowerCase() === "offer" || 
        a.status.toLowerCase() === "onboarding"
      );
      setApps(offerApps);
      if (offerApps.length > 0) {
        setSelectedApp(offerApps[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const loadOfferDetails = async (appId: number) => {
    try {
      const details = await apiService.getOffer(appId);
      setOffer(details);
    } catch (err) {
      console.error(err);
      setErrorMsg("Offer documentation is pending generation.");
    }
  };

  useEffect(() => {
    if (selectedApp) {
      loadOfferDetails(selectedApp.id);
    }
  }, [selectedApp]);

  const handleOfferResponse = async (accept: boolean) => {
    if (!offer) return;
    setErrorMsg("");
    setSuccessMsg("");
    try {
      await apiService.respondOffer(offer.id, accept);
      setSuccessMsg(accept ? "Offer Accepted! Welcome to the team." : "Offer declined.");
      await fetchData(); // Refetch status
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update offer decision.");
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto text-gray-500">
        Loading contracts portal...
      </div>
    );
  }

  if (apps.length === 0) {
    return (
      <div className="p-8 md:p-12 max-w-4xl mx-auto text-center flex flex-col justify-center items-center gap-4 min-h-[60vh]">
        <div className="w-12 h-12 rounded-2xl bg-purple-950/40 border border-purple-800/20 flex items-center justify-center text-purple-400">
          <Award size={24} />
        </div>
        <h1 className="text-xl font-bold text-white">No Offers Pending</h1>
        <p className="text-xs text-gray-500 max-w-sm">
          You have no pending offers or active onboarding workflows. Candidates will receive notifications as they complete the interview loop.
        </p>
      </div>
    );
  }

  const isOnboarding = selectedApp.status.toLowerCase() === "onboarding";

  return (
    <div className="p-8 md:p-12 max-w-6xl mx-auto flex flex-col gap-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <span>{isOnboarding ? "Employee Onboarding" : "Employment Offer"}</span>
          <Award className="text-purple-400" size={24} />
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          {isOnboarding 
            ? "Complete documents verification checklist to acquire credentials." 
            : "Review proposed salary benefits packages and accept employment contracts."}
        </p>
      </div>

      {successMsg && (
        <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-400 text-xs font-medium flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 rounded-xl bg-red-950/30 border border-red-800/40 text-red-400 text-xs font-medium">
          {errorMsg}
        </div>
      )}

      {!isOnboarding ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Offer Contract content */}
          <div className="lg:col-span-2 glass-panel p-8 rounded-2xl border border-gray-800 flex flex-col gap-6 bg-card/40">
            <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
              <FileText size={18} className="text-purple-400" />
              <span>Employment Agreement Contract</span>
            </h2>

            <div className="text-xs text-gray-300 leading-relaxed font-mono whitespace-pre-line p-5 rounded-xl border border-gray-800/60 bg-muted/60 h-96 overflow-y-auto">
              {offer ? (
                `# HireAI Employment Offer\n\nPosition: ${selectedApp.job.title}\nAnnual Salary Offered: $${offer.salary_offered.toLocaleString()} USD\nDepartment: ${selectedApp.job.department}\n\nDear Applicant,\n\nWe are extremely pleased to invite you to join HireAI as a full-time software developer. We were highly impressed by your results across the technical MCQ exam, algorithmic sandbox challenge, and speech diagnostic loop with Tara AI.\n\nUpon signing, you will be initialized in the onboarding tracker list where corporate identifiers, welcome packages, and communications tools will be provisioned automatically.`
              ) : (
                "Retrieving employment terms details..."
              )}
            </div>
          </div>

          {/* Action box */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-muted/40 flex flex-col gap-6 h-fit">
            <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
              <Building size={14} className="text-purple-400" />
              <span>Agreement Details</span>
            </h3>

            {offer && (
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Position Title:</span>
                  <span className="font-bold text-white text-right">{selectedApp.job.title}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Base Salary:</span>
                  <span className="font-bold text-emerald-400">${offer.salary_offered.toLocaleString()} USD</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Department:</span>
                  <span className="font-semibold text-gray-200">{selectedApp.job.department}</span>
                </div>

                <div className="border-t border-gray-800/80 pt-4 mt-2 flex flex-col gap-2">
                  <button
                    onClick={() => handleOfferResponse(true)}
                    className="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-2.5 text-xs font-bold transition-all shadow-md"
                  >
                    Accept Employment Offer
                  </button>
                  <button
                    onClick={() => handleOfferResponse(false)}
                    className="w-full bg-muted/50 border border-gray-800 text-gray-400 hover:text-red-400 hover:border-red-500/10 py-2.5 rounded-xl text-xs font-bold transition-all"
                  >
                    Decline Offer
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>
      ) : (
        /* Onboarding View */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div className="lg:col-span-2 glass-panel p-8 rounded-2xl border border-gray-800 flex flex-col gap-6 bg-card/40">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/30 text-emerald-400 text-xs font-semibold w-fit">
              <Sparkles size={14} className="animate-pulse" />
              <span>Welcome to HireAI!</span>
            </div>

            <h2 className="text-xl font-extrabold text-white">Your corporate profile is ready</h2>
            <p className="text-xs text-gray-400 leading-relaxed">
              The **Onboarding Agent** has successfully finalized your employee folder, created matching credentials, and dispatched welcome information to your mailbox.
            </p>

            <div className="border border-gray-800/80 rounded-2xl p-5 bg-muted/40 mt-2 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <span className="text-10 text-gray-500 font-bold uppercase tracking-wider block">Assigned employee ID</span>
                <span className="text-lg font-mono font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400 block mt-1">
                  HAI-2026-6819
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs text-emerald-400 font-semibold bg-emerald-950/20 border border-emerald-800/20 px-3 py-1.5 rounded-xl">
                <UserCheck size={14} />
                <span>Profile Verified</span>
              </div>
            </div>
          </div>

          {/* Checklist */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-muted/40 flex flex-col gap-4">
            <h3 className="text-xs font-bold text-white border-b border-gray-800 pb-3">
              Onboarding Checklist
            </h3>

            <div className="flex flex-col gap-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-purple-950/5 border border-purple-500/10 text-purple-300">
                <span className="flex items-center gap-2 font-semibold">
                  <CheckCircle2 size={14} className="text-purple-400" />
                  1. Setup Employee profile
                </span>
                <ChevronRight size={14} />
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-purple-950/5 border border-purple-500/10 text-purple-300">
                <span className="flex items-center gap-2 font-semibold">
                  <CheckCircle2 size={14} className="text-purple-400" />
                  2. Dispatch Welcome Packet
                </span>
                <Mail size={14} />
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl border border-gray-850 bg-background/40 text-gray-500">
                <span className="flex items-center gap-2">
                  <FileText size={14} />
                  3. Verify Tax W-4 documents
                </span>
                <ChevronRight size={14} />
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl border border-gray-850 bg-background/40 text-gray-500">
                <span className="flex items-center gap-2">
                  <Building size={14} />
                  4. Hardware Provisioning
                </span>
                <ChevronRight size={14} />
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
