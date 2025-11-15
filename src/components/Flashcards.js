import React, { useState } from "react";

export default function Flashcards({ flashcards }) {
  const [i, setI] = useState(0);
  if (!flashcards || flashcards.length === 0) return null;

  const card = flashcards[i];
  return (
    <div className="card">
      <h2>🧠 Flashcards</h2>
      <div className="flashcard">
        <strong>{card.q}</strong>
        <p>{card.a}</p>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button className="btn" onClick={() => setI(Math.max(0, i - 1))}>Prev</button>
        <span>{i + 1}/{flashcards.length}</span>
        <button className="btn" onClick={() => setI(Math.min(flashcards.length - 1, i + 1))}>Next</button>
      </div>
    </div>
  );
}
