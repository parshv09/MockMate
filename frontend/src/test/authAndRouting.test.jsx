import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as sessionsApi from "../api/sessions.api.js";
import * as resumesApi from "../api/resumes.api.js";
import { tokenStorage } from "../utils/tokenStorage.js";

function renderApp(initialEntries = ["/"]) {
  return render(
    <AuthProvider>
      <ToastProvider>
        <MemoryRouter initialEntries={initialEntries}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

describe("Authentication & Protected Routing", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    vi.restoreAllMocks();
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValue([]);
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
  });

  it("redirects unauthenticated users from /dashboard to /login", async () => {
    renderApp(["/dashboard"]);

    expect(
      await screen.findByRole("heading", { name: /sign in to mockmate/i })
    ).toBeInTheDocument();
  });

  it("does not flash protected content while session restoration is in progress", async () => {
    tokenStorage.setTokens({ access: "valid-access", refresh: "valid-refresh" });

    let resolveMe;
    vi.spyOn(authApi, "fetchCurrentUser").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveMe = resolve;
        })
    );

    renderApp(["/dashboard"]);

    expect(screen.getByRole("status", { name: /restoring session/i })).toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();

    resolveMe({
      id: 1,
      username: "alexchen",
      email: "alex@example.com",
      first_name: "Alex",
      last_name: "Chen",
      user_type: "student",
      target_role: "Backend Engineer",
    });

    expect(
      await screen.findByRole("heading", { name: /welcome back, alex/i })
    ).toBeInTheDocument();
  });

  it("completes registration and redirects to /dashboard", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "registerUser").mockResolvedValueOnce({
      message: "User registered successfully.",
      user: {
        id: 10,
        username: "alicesmith",
        email: "alice@example.com",
        first_name: "Alice",
        last_name: "Smith",
        user_type: "student",
        target_role: "Data Scientist",
      },
      tokens: { access: "new-access", refresh: "new-refresh" },
    });

    renderApp(["/register"]);

    await user.type(screen.getByLabelText(/first name/i), "Alice");
    await user.type(screen.getByLabelText(/last name/i), "Smith");
    await user.type(screen.getByLabelText(/^username/i), "alicesmith");
    await user.type(screen.getByLabelText(/^email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/target role/i), "Data Scientist");
    await user.type(screen.getByLabelText(/^password/i, { selector: "input" }), "SecurePass1");
    await user.type(screen.getByLabelText(/confirm password/i, { selector: "input" }), "SecurePass1");

    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByRole("heading", { name: /welcome back, alice/i })
    ).toBeInTheDocument();
    expect(tokenStorage.getAccessToken()).toBe("new-access");
  });

  it("displays backend validation errors on failed registration", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "registerUser").mockRejectedValueOnce({
      response: {
        status: 400,
        data: { username: ["This username is already taken."] },
      },
    });

    renderApp(["/register"]);

    await user.type(screen.getByLabelText(/first name/i), "Alice");
    await user.type(screen.getByLabelText(/last name/i), "Smith");
    await user.type(screen.getByLabelText(/^username/i), "existinguser");
    await user.type(screen.getByLabelText(/^email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/^password/i, { selector: "input" }), "SecurePass1");
    await user.type(screen.getByLabelText(/confirm password/i, { selector: "input" }), "SecurePass1");

    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findAllByText("This username is already taken.")).not.toHaveLength(0);
  });

  it("logs in successfully and redirects to /dashboard", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "loginUser").mockResolvedValueOnce({
      message: "Login successful.",
      user: {
        id: 2,
        username: "alexchen",
        email: "alex@example.com",
        first_name: "Alex",
        last_name: "Chen",
        user_type: "job_seeker",
        target_role: "Frontend Engineer",
      },
      tokens: { access: "login-access", refresh: "login-refresh" },
    });

    renderApp(["/login"]);

    await user.type(screen.getByLabelText(/username or email/i), "alexchen");
    await user.type(screen.getByLabelText(/^password/i), "Password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByRole("heading", { name: /welcome back, alex/i })
    ).toBeInTheDocument();
    expect(tokenStorage.getAccessToken()).toBe("login-access");
  });

  it("shows invalid credentials error on failed login", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "loginUser").mockRejectedValueOnce({
      response: {
        status: 400,
        data: { non_field_errors: ["Invalid credentials."] },
      },
    });

    renderApp(["/login"]);

    await user.type(screen.getByLabelText(/username or email/i), "wronguser");
    await user.type(screen.getByLabelText(/^password/i), "WrongPass1");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials.");
  });

  it("restores authenticated session on page refresh and redirects away from /login", async () => {
    tokenStorage.setTokens({ access: "stored-access", refresh: "stored-refresh" });
    vi.spyOn(authApi, "fetchCurrentUser").mockResolvedValueOnce({
      id: 3,
      username: "maya",
      email: "maya@example.com",
      first_name: "Maya",
      last_name: "Lin",
      user_type: "student",
      target_role: "",
    });

    renderApp(["/login"]);

    expect(
      await screen.findByRole("heading", { name: /welcome back, maya/i })
    ).toBeInTheDocument();
  });

  it("clears local tokens and redirects to /login on logout", async () => {
    const user = userEvent.setup();
    tokenStorage.setTokens({ access: "stored-access", refresh: "stored-refresh" });
    vi.spyOn(authApi, "fetchCurrentUser").mockResolvedValueOnce({
      id: 4,
      username: "sam",
      email: "sam@example.com",
      first_name: "Sam",
      last_name: "Lee",
      user_type: "student",
      target_role: "",
    });

    renderApp(["/dashboard"]);

    await screen.findByRole("heading", { name: /welcome back, sam/i });
    const signOutButtons = screen.getAllByRole("button", { name: /sign out/i });
    await user.click(signOutButtons[0]);

    await waitFor(() => {
      expect(tokenStorage.getAccessToken()).toBeNull();
      expect(tokenStorage.getRefreshToken()).toBeNull();
    });

    expect(
      await screen.findByRole("heading", { name: /sign in to mockmate/i })
    ).toBeInTheDocument();
  });
});

