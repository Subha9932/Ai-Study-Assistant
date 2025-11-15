import React, { useState } from "react";
import { summarizeText, summarizePDF, summarizeYouTube } from "../api";

export default function InputTabs({ onSummaryGenerated, loading, setLoading }) {
  const [activeTab, setActiveTab] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState("");

  const handleSummarize = async () => {
    if (activeTab === "text" && !text.trim()) {
      alert("Please enter some text");
      return;
    }
    if (activeTab === "pdf" && !file) {
      alert("Please upload a PDF file");
      return;
    }
    if (activeTab === "youtube" && !url.trim()) {
      alert("Please enter a YouTube URL");
      return;
    }

    setLoading(true);
    try {
      let res;
      if (activeTab === "text") {
        res = await summarizeText(text);
      } else if (activeTab === "pdf") {
        res = await summarizePDF(file);
      } else if (activeTab === "youtube") {
        res = await summarizeYouTube(url);
      }
      
      // Pass the full response object, not just summary text
      onSummaryGenerated({
        summary: res.summary || "No summary generated.",
        title: activeTab === "youtube" ? "YouTube Summary" : 
               activeTab === "pdf" ? file.name : "Text Summary"
      });
    } catch (e) {
      alert("Failed to summarize: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      {/* Tabs */}
      <div className="flex space-x-4 border-b pb-4 mb-6">
        <button
          onClick={() => setActiveTab("text")}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            activeTab === "text"
              ? "bg-indigo-600 text-white shadow-md"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          📝 Text
        </button>
        <button
          onClick={() => setActiveTab("pdf")}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            activeTab === "pdf"
              ? "bg-indigo-600 text-white shadow-md"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          📄 PDF
        </button>
        <button
          onClick={() => setActiveTab("youtube")}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            activeTab === "youtube"
              ? "bg-indigo-600 text-white shadow-md"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          🎥 YouTube
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-4">
        {activeTab === "text" && (
          <textarea
            placeholder="Paste your study material here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            className="w-full p-4 border-2 border-gray-200 rounded-lg focus:border-indigo-500 
                     focus:outline-none transition-colors resize-none"
          />
        )}

        {activeTab === "pdf" && (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setFile(e.target.files[0])}
              className="hidden"
              id="pdf-upload"
            />
            <label
              htmlFor="pdf-upload"
              className="cursor-pointer inline-flex items-center space-x-2 
                       bg-indigo-50 px-6 py-3 rounded-lg hover:bg-indigo-100 transition-colors"
            >
              <span className="text-2xl">📤</span>
              <span className="font-medium text-indigo-700">
                {file ? file.name : "Upload PDF"}
              </span>
            </label>
          </div>
        )}

        {activeTab === "youtube" && (
          <input
            type="url"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full p-4 border-2 border-gray-200 rounded-lg focus:border-indigo-500 
                     focus:outline-none transition-colors"
          />
        )}

        {/* Generate Summary Button */}
        <button
          onClick={handleSummarize}
          disabled={loading}
          className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-4 
                   rounded-lg font-semibold text-lg hover:from-indigo-700 hover:to-purple-700
                   disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed
                   transition-all duration-200 shadow-lg hover:shadow-xl"
        >
          {loading ? "⏳ Generating Summary..." : "✨ Generate Summary"}
        </button>
      </div>
    </div>
  );
}
