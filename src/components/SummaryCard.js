import React from "react";
import ReactMarkdown from "react-markdown";

export default function SummaryCard({ data, onGenerateQuiz, quizLoading }) {
  if (!data || !data.summary) {
    return null;
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">📋</span>
          <h2 className="text-2xl font-bold text-gray-800">Summary</h2>
        </div>
        
        {/* Generate Quiz Button */}
        <button
          onClick={onGenerateQuiz}
          disabled={quizLoading}
          className="bg-gradient-to-r from-green-500 to-teal-600 text-white px-6 py-2 
                   rounded-lg font-semibold hover:from-green-600 hover:to-teal-700
                   disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed
                   transition-all duration-200 shadow-md hover:shadow-lg flex items-center space-x-2"
        >
          <span>{quizLoading ? "⏳" : "🎯"}</span>
          <span>{quizLoading ? "Generating..." : "Generate Quiz"}</span>
        </button>
      </div>
      
      {/* Markdown Content */}
      <div className="prose prose-lg max-w-none prose-headings:text-gray-800 
                    prose-p:text-gray-700 prose-strong:text-indigo-700 
                    prose-ul:text-gray-700 prose-ol:text-gray-700
                    prose-li:marker:text-indigo-600 prose-blockquote:border-indigo-500
                    prose-code:bg-gray-100 prose-code:text-indigo-600 
                    prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                    prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline">
        <ReactMarkdown>{data.summary}</ReactMarkdown>
      </div>
    </div>
  );
}
