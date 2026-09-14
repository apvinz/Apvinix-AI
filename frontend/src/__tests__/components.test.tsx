import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UploadZone } from "../components/UploadZone";
import { StepIndicator } from "../components/StepIndicator";

describe("StepIndicator", () => {
  it("renders all six workflow steps", () => {
    render(<StepIndicator current="Choose" />);
    ["Upload", "Analyze", "Choose", "Transcribe", "Review", "Export"].forEach((step) => {
      expect(screen.getByText(step)).toBeInTheDocument();
    });
  });
});

describe("UploadZone", () => {
  it("rejects an unsupported file extension with a real client-side error", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);
    const input = screen.getByRole("button").querySelector("input")!;
    const badFile = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [badFile] } });
    expect(screen.getByText(/Unsupported file type/i)).toBeInTheDocument();
    expect(onFileSelected).not.toHaveBeenCalled();
  });

  it("accepts a valid audio file and calls onFileSelected", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);
    const input = screen.getByRole("button").querySelector("input")!;
    const goodFile = new File(["fake-audio-bytes"], "song.wav", { type: "audio/wav" });
    Object.defineProperty(goodFile, "size", { value: 1024 });
    fireEvent.change(input, { target: { files: [goodFile] } });
    expect(onFileSelected).toHaveBeenCalledWith(goodFile);
  });
});
