const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

// ==================== AUTH HELPERS ====================

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

const handleAuthError = async (res) => {
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      throw new Error('Session expired. Please login again.');
    }
    return true;
  }
  return false;
};

// ==================== AUTHENTICATION APIs ====================

export async function registerUser(email, phone, fullName) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      email, 
      phone: phone || "", 
      full_name: fullName 
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Registration failed");
  }
  return res.json();
}

export async function sendOTP(phone, email) {
  const res = await fetch(`${API_BASE}/api/auth/send-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      email: email,
      phone: phone 
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to send OTP");
  }
  return res.json();
}

export async function verifyOTP(email, otp) {
  const res = await fetch(`${API_BASE}/api/auth/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      email: email,
      otp: otp 
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Invalid OTP");
  }

  const data = await res.json();
  
  // Store tokens in localStorage
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  
  return data;
}

export async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    localStorage.setItem('access_token', data.access_token);
    return true;
  } catch (error) {
    return false;
  }
}

export async function getUserProfile() {
  const res = await fetch(`${API_BASE}/api/user/profile`, {
    headers: getAuthHeaders(),
  });

  if (await handleAuthError(res)) {
    return getUserProfile();
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch profile");
  }
  return res.json();
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

// ==================== SUMMARIZATION APIs (Now Protected) ====================

export async function summarizeText(text) {
  const res = await fetch(`${API_BASE}/api/summarize`, {
    method: "POST",
    headers: getAuthHeaders(), // ✅ NOW SENDS TOKEN
    body: JSON.stringify({ text }),
  });

  if (await handleAuthError(res)) {
    return summarizeText(text);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to summarize text");
  }
  return res.json();
}

export async function summarizeYouTube(url) {
  const res = await fetch(`${API_BASE}/api/summarize`, {
    method: "POST",
    headers: getAuthHeaders(), // ✅ NOW SENDS TOKEN
    body: JSON.stringify({ youtube_url: url }),
  });

  if (await handleAuthError(res)) {
    return summarizeYouTube(url);
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const errorMessage = errorData.detail || `HTTP ${res.status}: Failed to summarize YouTube`;
    throw new Error(errorMessage);
  }

  return res.json();
}

export async function summarizePDF(file) {
  const formData = new FormData();
  formData.append("file", file);
  
  const token = localStorage.getItem('access_token');
  const res = await fetch(`${API_BASE}/api/summarize-pdf`, {
    method: "POST",
    headers: {
      ...(token && { 'Authorization': `Bearer ${token}` }) // ✅ NOW SENDS TOKEN
    },
    body: formData,
  });

  if (await handleAuthError(res)) {
    return summarizePDF(file);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to summarize PDF");
  }
  return res.json();
}

// ==================== QUIZ APIs (Now Protected) ====================

export async function generateQuiz(summary) {
  const res = await fetch(`${API_BASE}/api/quiz`, {
    method: "POST",
    headers: getAuthHeaders(), // ✅ NOW SENDS TOKEN
    body: JSON.stringify({ text: summary }),
  });

  if (await handleAuthError(res)) {
    return generateQuiz(summary);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate quiz");
  }
  return res.json();
}

export async function downloadQuizPdf(title, quizData) {
  try {
    const res = await fetch(`${API_BASE}/api/download-quiz`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, quiz_data: quizData }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to download PDF");
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${title}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Download failed:", error);
    throw error;
  }
}

// ==================== USER HISTORY APIs ====================

export async function getUserSummaries() {
  const res = await fetch(`${API_BASE}/api/user/summaries`, {
    headers: getAuthHeaders(),
  });

  if (await handleAuthError(res)) {
    return getUserSummaries();
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch summaries");
  }
  return res.json();
}

export async function getUserQuizzes() {
  const res = await fetch(`${API_BASE}/api/user/quizzes`, {
    headers: getAuthHeaders(),
  });

  if (await handleAuthError(res)) {
    return getUserQuizzes();
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch quizzes");
  }
  return res.json();
}
