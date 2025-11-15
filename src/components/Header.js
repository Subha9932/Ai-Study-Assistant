import React from "react";

export default function Header() {
  return (
    <header className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-8 shadow-lg">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-4xl font-bold mb-2">🧠 AI Study Assistant</h1>
        <p className="text-indigo-100 text-lg">
          Summarize notes, PDFs, or YouTube videos — get quizzes instantly!
        </p>
      </div>
    </header>
  );
}
