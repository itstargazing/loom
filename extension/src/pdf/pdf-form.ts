import {
  PDFCheckBox,
  PDFDocument,
  PDFDropdown,
  PDFRadioGroup,
  PDFSignature,
  PDFTextField,
  type PDFField,
} from "pdf-lib";

import type { PdfFormField, PdfFormFieldType, PdfFormSnapshot } from "./types";

function mapFieldType(field: PDFField): PdfFormFieldType {
  if (field instanceof PDFTextField) return "text";
  if (field instanceof PDFCheckBox) return "checkbox";
  if (field instanceof PDFDropdown) return "dropdown";
  if (field instanceof PDFRadioGroup) return "radio";
  if (field instanceof PDFSignature) return "signature";

  const name = field.constructor.name.toLowerCase();
  if (name.includes("text")) return "text";
  if (name.includes("check")) return "checkbox";
  if (name.includes("dropdown") || name.includes("option")) return "dropdown";
  if (name.includes("radio")) return "radio";
  if (name.includes("signature")) return "signature";
  if (name.includes("date")) return "date";

  return "unknown";
}

function readFieldValue(field: PDFField, type: PdfFormFieldType): string | boolean | null {
  try {
    if (field instanceof PDFCheckBox) {
      return field.isChecked();
    }
    if (field instanceof PDFTextField) {
      return field.getText() ?? "";
    }
    if (field instanceof PDFDropdown) {
      const selected = field.getSelected();
      return selected.length > 0 ? selected[0] : "";
    }
    if (field instanceof PDFRadioGroup) {
      return field.getSelected() ?? "";
    }
    if (type === "signature") {
      return null;
    }
  } catch {
    return null;
  }
  return null;
}

function readFieldOptions(field: PDFField): string[] | undefined {
  try {
    if (field instanceof PDFDropdown) {
      return field.getOptions();
    }
    if (field instanceof PDFRadioGroup) {
      return field.getOptions();
    }
  } catch {
    return undefined;
  }
  return undefined;
}

/** Extract AcroForm fields from PDF bytes. Returns empty fields if none exist. */
export async function extractFormFields(
  bytes: Uint8Array,
  url: string,
): Promise<PdfFormSnapshot> {
  const pdfDoc = await PDFDocument.load(bytes, { ignoreEncryption: true });
  const form = pdfDoc.getForm();
  const rawFields = form.getFields();

  if (rawFields.length === 0) {
    return { url, hasFormFields: false, fields: [] };
  }

  const fields: PdfFormField[] = rawFields.map((field) => {
    const type = mapFieldType(field);
    return {
      name: field.getName(),
      type,
      value: readFieldValue(field, type),
      options: readFieldOptions(field),
    };
  });

  return {
    url,
    hasFormFields: true,
    fields,
  };
}

/** Write field values into a PDF and return the filled bytes. */
export async function fillPdfFormFields(
  bytes: Uint8Array,
  values: Record<string, string | boolean>,
): Promise<Uint8Array> {
  const pdfDoc = await PDFDocument.load(bytes, { ignoreEncryption: true });
  const form = pdfDoc.getForm();

  for (const [name, value] of Object.entries(values)) {
    let field: PDFField;
    try {
      field = form.getField(name);
    } catch {
      continue;
    }

    if (typeof value === "boolean" && field instanceof PDFCheckBox) {
      if (value) {
        field.check();
      } else {
        field.uncheck();
      }
      continue;
    }

    if (typeof value === "string") {
      if (field instanceof PDFTextField) {
        field.setText(value);
      } else if (field instanceof PDFDropdown) {
        field.select(value);
      } else if (field instanceof PDFRadioGroup) {
        field.select(value);
      }
    }
  }

  form.updateFieldAppearances();
  return pdfDoc.save();
}

/** Trigger a browser download of PDF bytes. */
export function downloadPdfBytes(bytes: Uint8Array, filename: string): void {
  // Blob's signature wants an ArrayBuffer-backed view, while Uint8Array is
  // generic over ArrayBufferLike. These bytes always come from pdf-lib's save(),
  // so they are never SharedArrayBuffer-backed.
  const blob = new Blob([bytes as Uint8Array<ArrayBuffer>], {
    type: "application/pdf",
  });
  const objectUrl = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
  // Chrome ignores clicks on anchors that are not in the document.
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  // Revoking synchronously can cancel the download before it starts.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

function filenameFromUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const segment = parsed.pathname.split("/").pop();
    if (segment && segment.toLowerCase().endsWith(".pdf")) {
      return decodeURIComponent(segment);
    }
  } catch {
    // fall through
  }
  return "document.pdf";
}

export { filenameFromUrl };
