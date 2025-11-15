import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import InputTabs from "./components/InputTabs";
import SummaryCard from "./components/SummaryCard";
import QuizPlayground from "./components/QuizPlayground";
import Login from "./components/Login";
import { generateQuiz, getUserProfile, logout } from "./api";
import "./App.css";

export default function App() {
  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // App State
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [quiz, setQuiz] = useState([]);
  const [quizOpen, setQuizOpen] = useState(false);
  const [quizLoading, setQuizLoading] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      setAuthLoading(false);
      return;
    }

    try {
      const profile = await getUserProfile();
      setUser(profile.profile);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Auth check failed:", error);
      setIsAuthenticated(false);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    logout();
    setIsAuthenticated(false);
    setUser(null);
    setSummaryData(null);
    setQuiz([]);
  };

  const handleGenerateQuiz = async () => {
    if (!summaryData?.summary) {
      alert("Generate summary first!");
      return;
    }

    setQuizLoading(true);
    try {
      const res = await generateQuiz(summaryData.summary);
      setQuiz(res.questions || []);
      setQuizOpen(true);
    } catch (e) {
      alert("Failed to generate quiz: " + e.message);
    } finally {
      setQuizLoading(false);
    }
  };

  // Show loading spinner while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-white mx-auto mb-4"></div>
          <p className="text-white text-lg font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  // Main application (authenticated users only)
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
      <Header user={user} onLogout={handleLogout} />

      <main className="container mx-auto px-4 py-8 max-w-5xl">
        {/* User Welcome Section */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-3">
            Welcome back, {user?.full_name || user?.email}! 👋
          </h1>
          <p className="text-lg text-gray-600">
            Transform your study materials into summaries and interactive quizzes
          </p>
        </div>

        {/* Input Section */}
        <InputTabs 
          onSummaryGenerated={setSummaryData} 
          loading={loading} 
          setLoading={setLoading} 
        />

        {/* Summary Display */}
        {summaryData && (
          <SummaryCard
            data={summaryData}
            onGenerateQuiz={handleGenerateQuiz}
            quizLoading={quizLoading}
          />
        )}

        {/* Quiz Modal */}
        {quizOpen && quiz.length > 0 && (
          <QuizPlayground
            questions={quiz}
            title={summaryData?.title || "Quiz"}
            onClose={() => setQuizOpen(false)}
          />
        )}

        {/* Loading Overlay */}
        {loading && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-indigo-600 mx-auto mb-4"></div>
              <p className="text-lg font-medium text-gray-700">Generating summary...</p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-gray-600">
        <p>🤖 Powered by Google Gemini AI | Secure OTP Authentication</p>
      </footer>
    </div>
  );
}
