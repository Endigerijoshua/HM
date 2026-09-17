import { PagePlaceholder } from "../components/Placeholder";

export default function AdminBoundaryPage() {
  return (
    <PagePlaceholder
      title="Admin Boundary Management"
      description="Manage jurisdiction versions, upload GeoJSON boundaries, set effective dates and compare historical vs proposed layouts - always append-only, never destructive."
      note="P1-P3"
    />
  );
}