import ClassicTemplate from "./templates/ClassicTemplate";
import ExecutiveTemplate from "./templates/ExecutiveTemplate";
import VividTemplate from "./templates/VividTemplate";

const TEMPLATES = {
  classic: ClassicTemplate,
  executive: ExecutiveTemplate,
  vivid: VividTemplate,
};

export default function InvoiceDocument({ invoice, org = {} }) {
  const Template = TEMPLATES[org.document_template] ?? ClassicTemplate;
  return <Template org={org} doc={invoice} type="invoice" />;
}
