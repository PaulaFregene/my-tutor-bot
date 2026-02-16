import { redirect } from "next/navigation";

export default function HomePage() {
  // Redirect to /chat after login
  redirect("/chat");
}
