import React, { useState, useEffect } from 'react';
import { registerUser, sendOTP, verifyOTP } from '../api';
import '../Login.css';

export default function Login({ onLoginSuccess }) {
  const [mode, setMode] = useState('login');
  const [step, setStep] = useState('email');
  
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [otp, setOtp] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [timer, setTimer] = useState(0);

  useEffect(() => {
    if (timer > 0) {
      const interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [timer]);

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await registerUser(email, '', fullName);
      
      // Auto-send OTP after registration
      await sendOTP(null, email);
      setStep('otp');
      setTimer(300);
      
      alert('Registration successful! Check your email (or console) for OTP.');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSendOTP = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await sendOTP(null, email);
      setStep('otp');
      setTimer(300);
      
      alert('OTP sent! Check your email (or backend console for development).');
    } catch (err) {
      setError(err.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Pass EMAIL (not phone) to verifyOTP
      const data = await verifyOTP(email, otp);
      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.message || 'Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = () => {
    if (timer > 0) return;
    handleSendOTP();
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>🎓 AI Study Assistant</h1>
          <p>Transform your learning with AI-powered summaries and quizzes</p>
        </div>

        {step === 'email' && (
          <>
            <div className="mode-toggle">
              <button 
                className={mode === 'login' ? 'active' : ''} 
                onClick={() => setMode('login')}
              >
                Login
              </button>
              <button 
                className={mode === 'register' ? 'active' : ''} 
                onClick={() => setMode('register')}
              >
                Register
              </button>
            </div>

            {mode === 'register' ? (
              <form onSubmit={handleRegister} className="auth-form">
                <h2>Create Account</h2>
                
                <input
                  type="text"
                  placeholder="Full Name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
                
                <input
                  type="email"
                  placeholder="Email Address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                
                <button type="submit" disabled={loading}>
                  {loading ? 'Registering...' : 'Register & Send OTP'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleSendOTP} className="auth-form">
                <h2>Welcome Back</h2>
                
                <input
                  type="email"
                  placeholder="Email Address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                
                <button type="submit" disabled={loading}>
                  {loading ? 'Sending OTP...' : 'Send OTP to Email'}
                </button>
              </form>
            )}
          </>
        )}

        {step === 'otp' && (
          <form onSubmit={handleVerifyOTP} className="auth-form">
            <h2>Enter Verification Code</h2>
            <p className="otp-info">📧 Code sent to {email}</p>
            <div className="otp-notice">
              <strong>Development Mode:</strong><br/>
              Check your backend console for the OTP code
            </div>
            
            <input
              type="text"
              placeholder="Enter 6-digit OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              maxLength={6}
              autoFocus
              required
            />
            
            <button type="submit" disabled={loading || otp.length !== 6}>
              {loading ? 'Verifying...' : 'Verify & Login'}
            </button>

            <div className="resend-section">
              {timer > 0 ? (
                <p>Resend OTP in {formatTime(timer)}</p>
              ) : (
                <button type="button" onClick={handleResendOTP} className="link-button">
                  Resend OTP
                </button>
              )}
            </div>

            <button 
              type="button" 
              onClick={() => {
                setStep('email');
                setOtp('');
                setError('');
              }} 
              className="back-button"
            >
              ← Change Email Address
            </button>
          </form>
        )}

        {error && <div className="error-message">{error}</div>}

        <div className="login-features">
          <div className="feature">
            <span>🔒</span>
            <p>Secure Email OTP</p>
          </div>
          <div className="feature">
            <span>📚</span>
            <p>AI-Powered Summaries</p>
          </div>
          <div className="feature">
            <span>🎯</span>
            <p>Interactive Quizzes</p>
          </div>
        </div>
      </div>
    </div>
  );
}
