export class VerificationError extends Error {
  constructor(message: string, public metadata: any) {
    super(message);
    this.name = "VerificationError";
  }

  toString() {
    return `${this.message}\n${this.metadata.join("\n")}`;
  }
}

export function errorStatus(error: unknown) {
  if (error instanceof VerificationError)
    return { status: "failed", error: error.metadata };

  return { status: "failed", error: String(error) };
}
