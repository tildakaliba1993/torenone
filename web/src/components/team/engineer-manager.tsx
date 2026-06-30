"use client";

import { useState } from "react";

import { setEngineerStatus } from "@/app/(app)/dashboard/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface FirmMember {
  id: string;
  name: string | null;
  is_registered_engineer: boolean;
  ecsa_reg_no: string | null;
}

/**
 * Registered-engineer management. The firm owner can mark colleagues as registered (ECSA)
 * engineers (with their registration number) — only they may apply an e-stamp to a calc
 * package. Non-owners see a read-only roster.
 */
export function EngineerManager({
  members,
  isOwner,
  selfId,
}: {
  members: FirmMember[];
  isOwner: boolean;
  selfId: string;
}) {
  if (members.length === 0) {
    return <p className="text-sm text-muted">No team members yet.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      {members.map((m) => (
        <MemberRow key={m.id} member={m} isOwner={isOwner} selfId={selfId} />
      ))}
    </div>
  );
}

function MemberRow({
  member,
  isOwner,
  selfId,
}: {
  member: FirmMember;
  isOwner: boolean;
  selfId: string;
}) {
  const [isEng, setIsEng] = useState(member.is_registered_engineer);
  const [reg, setReg] = useState(member.ecsa_reg_no ?? "");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const label = member.name?.trim() || (member.id === selfId ? "You" : member.id.slice(0, 8));

  async function onSave() {
    setSaving(true);
    setStatus("idle");
    setError(null);
    const res = await setEngineerStatus({
      memberId: member.id,
      isRegisteredEngineer: isEng,
      ecsaRegNo: reg,
    });
    setSaving(false);
    if (res.error) {
      setStatus("error");
      setError(res.error);
    } else {
      setStatus("saved");
    }
  }

  if (!isOwner) {
    return (
      <div className="flex items-center justify-between gap-4 border-b border-border py-2 text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted">
          {member.is_registered_engineer
            ? `Registered engineer · ECSA ${member.ecsa_reg_no ?? "—"}`
            : "Not a registered engineer"}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3 text-sm">
      <div className="flex items-center justify-between gap-4">
        <span className="font-medium">{label}</span>
        <label className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={isEng}
            onChange={(e) => {
              setStatus("idle");
              setIsEng(e.target.checked);
            }}
            className="h-4 w-4 accent-[var(--primary)]"
          />
          <span>Registered engineer</span>
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="ECSA registration no."
          value={reg}
          disabled={!isEng}
          onChange={(e) => {
            setStatus("idle");
            setReg(e.target.value);
          }}
          className="max-w-xs"
        />
        <Button onClick={onSave} loading={saving} variant="secondary">
          {saving ? "Saving…" : "Save"}
        </Button>
        {status === "saved" ? <span className="text-xs text-success">Saved.</span> : null}
        {status === "error" ? (
          <span role="alert" className="text-xs text-danger">
            {error}
          </span>
        ) : null}
      </div>
    </div>
  );
}
