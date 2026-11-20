import { useParams } from "react-router-dom";
import { InterviewWorkspace } from "../components/interview/InterviewWorkspace.jsx";

export function InterviewWorkspacePage() {
  const { id } = useParams();
  return <InterviewWorkspace sessionId={id} />;
}
