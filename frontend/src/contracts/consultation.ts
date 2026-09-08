export type ConsultationStatus =
  | "transcribing"
  | "extracting"
  | "succeeded"
  | "failed";

export type ConsultationAccepted = {
  id: string;
  status: ConsultationStatus;
};

export type SoapNote = {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
};

export type Medication = {
  name: string;
  dosage: string;
  route: string;
  frequency: string;
  duration: string;
  instructions: string;
};

export type Prescription = {
  medications: Medication[];
};

export type ExamOrder = {
  name: string;
  indication: string;
  instructions: string;
};

export type ExamOrders = {
  exams: ExamOrder[];
};

export type ConsultationDocuments = {
  medical_record: SoapNote;
  prescription: Prescription;
  exam_orders: ExamOrders;
};

export type ConsultationRead = {
  id: string;
  status: ConsultationStatus;
  documents: ConsultationDocuments | null;
  error: string | null;
};

export function emptyMedication(): Medication {
  return {
    name: "",
    dosage: "",
    route: "",
    frequency: "",
    duration: "",
    instructions: "",
  };
}

export function emptyExamOrder(): ExamOrder {
  return {
    name: "",
    indication: "",
    instructions: "",
  };
}
