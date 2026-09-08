export type DocumentHeader = {
  patientName: string;
  doctorName: string;
  crm: string;
  city: string;
  date: string;
};

export function emptyDocumentHeader(): DocumentHeader {
  return {
    patientName: "",
    doctorName: "",
    crm: "",
    city: "",
    date: new Intl.DateTimeFormat("pt-BR").format(new Date()),
  };
}
