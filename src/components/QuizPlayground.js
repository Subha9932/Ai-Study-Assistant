import React, { useState } from "react";
import { downloadQuizPdf } from "../api";

export default function QuizPlayground({ questions, title, onClose }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [score, setScore] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);

  // Safety check: if no questions, show error
  if (!questions || questions.length === 0) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl p-8 max-w-md">
          <h2 className="text-2xl font-bold text-red-600 mb-4">No Questions Available</h2>
          <p className="text-gray-700 mb-6">Unable to load quiz questions. Please try generating again.</p>
          <button
            onClick={onClose}
            className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const question = questions[currentIndex];

  const handleAnswer = (qIdx, optionIdx) => {
    setAnswers({ ...answers, [qIdx]: optionIdx });
    setShowExplanation(false);
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setShowExplanation(false);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setShowExplanation(false);
    }
  };

  const handleSubmit = () => {
    let total = 0;
    questions.forEach((q, i) => {
      if (answers[i] === q.answer_index) total++;
    });
    setScore(total);
  };

  const handleDownload = async () => {
    try {
      await downloadQuizPdf(title || "AI_Study_Quiz", questions);
    } catch (error) {
      alert("Failed to download quiz: " + error.message);
    }
  };

  const handleClose = () => {
    onClose();
  };

  const handleRetake = () => {
    setCurrentIndex(0);
    setAnswers({});
    setScore(null);
    setShowExplanation(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {!score ? (
          <div className="p-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-3xl font-bold text-gray-800">{title || "Quiz"}</h2>
                <p className="text-gray-600 mt-1">
                  Question {currentIndex + 1} of {questions.length}
                </p>
              </div>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 text-3xl font-bold"
              >
                ×
              </button>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-gray-200 rounded-full h-2 mb-6">
              <div
                className="bg-gradient-to-r from-indigo-600 to-purple-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
              ></div>
            </div>

            {/* Question */}
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">
                {question.question}
              </h3>

              {/* Options */}
              <div className="space-y-3">
                {question.options && question.options.map((opt, i) => (
                  <button
                    key={i}
                    onClick={() => handleAnswer(currentIndex, i)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                      answers[currentIndex] === i
                        ? "border-indigo-600 bg-indigo-50 text-indigo-900"
                        : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
                    }`}
                  >
                    <span className="font-semibold">{String.fromCharCode(65 + i)}.</span> {opt}
                  </button>
                ))}
              </div>

              {/* Explanation */}
              {answers[currentIndex] !== undefined && question.explanation && (
                <div className="mt-4">
                  <button
                    onClick={() => setShowExplanation(!showExplanation)}
                    className="text-indigo-600 hover:text-indigo-800 font-medium text-sm"
                  >
                    {showExplanation ? "Hide" : "Show"} Explanation
                  </button>
                  {showExplanation && (
                    <div className="mt-2 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <p className="text-sm font-semibold text-blue-900 mb-1">
                        Correct Answer: {String.fromCharCode(65 + question.answer_index)}
                      </p>
                      <p className="text-sm text-blue-800">{question.explanation}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Navigation */}
            <div className="flex justify-between items-center mt-8">
              <button
                onClick={handlePrev}
                disabled={currentIndex === 0}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-medium
                         hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
              >
                ⬅ Prev
              </button>

              {currentIndex === questions.length - 1 ? (
                <button
                  onClick={handleSubmit}
                  disabled={Object.keys(answers).length !== questions.length}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium
                           hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed
                           transition-colors"
                >
                  Submit ✅
                </button>
              ) : (
                <button
                  onClick={handleNext}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium
                           hover:bg-indigo-700 transition-colors"
                >
                  Next ➡
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Score Card */
          <div className="p-8 text-center">
            <div className="text-6xl mb-4">
              {score === questions.length ? "🎉" : score >= questions.length / 2 ? "🎯" : "📚"}
            </div>
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Quiz Completed!</h2>
            <div className="text-5xl font-bold text-indigo-600 mb-4">
              {score}/{questions.length}
            </div>
            <p className="text-xl text-gray-700 mb-8">
              {score === questions.length
                ? "Perfect score! Excellent work! 🌟"
                : score >= questions.length / 2
                ? "Good job! Keep studying! 💪"
                : "Keep practicing! You'll improve! 📖"}
            </p>

            {/* Detailed Results */}
            <div className="bg-gray-50 rounded-lg p-6 mb-6 text-left max-h-96 overflow-y-auto">
              <h3 className="font-bold text-lg mb-4 text-gray-800">Review Your Answers:</h3>
              {questions.map((q, i) => (
                <div key={i} className="mb-4 p-4 bg-white rounded-lg border">
                  <p className="font-semibold text-gray-800 mb-2">
                    Q{i + 1}: {q.question}
                  </p>
                  <div className="flex items-center space-x-2 text-sm">
                    <span className="text-gray-600">Your answer:</span>
                    <span
                      className={
                        answers[i] === q.answer_index
                          ? "text-green-600 font-semibold"
                          : "text-red-600 font-semibold"
                      }
                    >
                      {answers[i] !== undefined
                        ? String.fromCharCode(65 + answers[i])
                        : "Not answered"}
                    </span>
                    {answers[i] !== q.answer_index && (
                      <span className="text-gray-600">
                        (Correct: {String.fromCharCode(65 + q.answer_index)})
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-4">
              <button
                onClick={handleRetake}
                className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-semibold
                         hover:bg-indigo-700 transition-colors"
              >
                🔄 Retake Quiz
              </button>
              <button
                onClick={handleDownload}
                className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold
                         hover:bg-green-700 transition-colors"
              >
                ⬇ Download PDF
              </button>
              <button
                onClick={handleClose}
                className="flex-1 bg-gray-600 text-white py-3 rounded-lg font-semibold
                         hover:bg-gray-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
