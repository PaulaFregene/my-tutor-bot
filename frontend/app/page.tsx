import { redirect } from "next/navigation";

export default function HomePage() {
  // Redirect to /chat after login
  redirect("/chat");
}


// export default function HomePage() {
//   return (
//     <div className="max-w-2xl mx-auto p-4 text-center">
//       <h1 className="text-3xl font-bold mb-4">Welcome to My-Tutor-Bot</h1>
//       <h2> Focusing on CS211 - Professor Zhang</h2>
//       <p>Login or sign up to start interacting with course content.</p>
//     </div>
//   );
// }

