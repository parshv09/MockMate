
"""
Unit and integration test suite for MockMate Phase 4A REST APIs:
- Authentication endpoints (/api/v1/auth/*)
- Resume endpoints (/api/v1/resumes/*)
"""

import os
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from interviewapp.api.serializers.resume_serializers import ResumeUploadSerializer
from interviewapp.models import (
    Answer,
    GeneratedQuestion,
    InterviewSession,
    Resume,
    SessionQuestion,
    UserProfile,
)
from interviewapp.services.resume_service import (
    cleanup_resume_assets,
    delete_candidate_resume,
    validate_resume_file,
)

User = get_user_model()


class AuthAPITests(APITestCase):
    """
    Test suite for Authentication REST endpoints:
    - POST /api/v1/auth/register/
    - POST /api/v1/auth/login/
    - POST /api/v1/auth/refresh/
    - GET /api/v1/auth/me/
    """

    def setUp(self):
        self.register_url = reverse("api_v1:auth_register")
        self.login_url = reverse("api_v1:auth_login")
        self.refresh_url = reverse("api_v1:auth_refresh")
        self.me_url = reverse("api_v1:auth_me")

        self.user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="ExistingPassword123",
            first_name="Existing",
            last_name="User",
        )
        UserProfile.objects.create(
            user=self.user,
            user_type="job_seeker",
            target_role="Full Stack Engineer",
        )

    def test_register_success(self):
        payload = {
            "first_name": "Alice",
            "last_name": "Smith",
            "username": "alicesmith",
            "email": "alice@example.com",
            "password": "SecurePassword1",
            "confirm_password": "SecurePassword1",
            "user_type": "student",
            "target_role": "Data Scientist",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["username"], "alicesmith")
        self.assertEqual(user_data["email"], "alice@example.com")
        self.assertEqual(user_data["first_name"], "Alice")
        self.assertEqual(user_data["last_name"], "Smith")
        self.assertEqual(user_data["user_type"], "student")
        self.assertEqual(user_data["target_role"], "Data Scientist")
        self.assertNotIn("password", user_data)

        # Verify DB records
        created_user = User.objects.get(username="alicesmith")
        self.assertEqual(created_user.profile.user_type, "student")
        self.assertEqual(created_user.profile.target_role, "Data Scientist")

    def test_register_duplicate_username(self):
        payload = {
            "first_name": "Another",
            "last_name": "User",
            "username": "existinguser",
            "email": "newemail@example.com",
            "password": "SecurePassword1",
            "confirm_password": "SecurePassword1",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_register_duplicate_email(self):
        payload = {
            "first_name": "Another",
            "last_name": "User",
            "username": "newuser",
            "email": "existing@example.com",
            "password": "SecurePassword1",
            "confirm_password": "SecurePassword1",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_password_mismatch(self):
        payload = {
            "first_name": "Mismatch",
            "last_name": "User",
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password": "SecurePassword1",
            "confirm_password": "DifferentPassword2",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_register_weak_password_no_digit(self):
        payload = {
            "first_name": "Weak",
            "last_name": "Password",
            "username": "weakuser1",
            "email": "weak1@example.com",
            "password": "NoDigitsInThisPassword",
            "confirm_password": "NoDigitsInThisPassword",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_weak_password_no_uppercase(self):
        payload = {
            "first_name": "Weak",
            "last_name": "Password",
            "username": "weakuser2",
            "email": "weak2@example.com",
            "password": "nouppercasehere123",
            "confirm_password": "nouppercasehere123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_weak_password_no_lowercase(self):
        payload = {
            "first_name": "Weak",
            "last_name": "Password",
            "username": "weakuser3",
            "email": "weak3@example.com",
            "password": "NOLOWERCASEHERE123",
            "confirm_password": "NOLOWERCASEHERE123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_login_success_with_username(self):
        payload = {
            "username": "existinguser",
            "password": "ExistingPassword123",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertEqual(response.data["user"]["username"], "existinguser")

    def test_login_success_with_email(self):
        payload = {
            "username": "existing@example.com",
            "password": "ExistingPassword123",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertEqual(response.data["user"]["username"], "existinguser")

    def test_login_invalid_password(self):
        payload = {
            "username": "existinguser",
            "password": "WrongPassword999",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        payload = {
            "username": "nonexistentuser",
            "password": "SomePassword123",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_auth_me_authenticated(self):
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "existinguser")
        self.assertEqual(response.data["email"], "existing@example.com")
        self.assertEqual(response.data["user_type"], "job_seeker")
        self.assertEqual(response.data["target_role"], "Full Stack Engineer")

    def test_auth_me_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        payload = {"refresh": str(refresh)}
        response = self.client.post(self.refresh_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_register_when_userprofile_already_exists(self):
        payload = {
            "first_name": "Signal",
            "last_name": "User",
            "username": "signaluser",
            "email": "signal@example.com",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123",
            "user_type": "job_seeker",
            "target_role": "Cloud Architect",
        }

        # Simulate a post_save signal that auto-created a default profile
        orig_create_user = User.objects.create_user

        def fake_create_user(*args, **kwargs):
            u = orig_create_user(*args, **kwargs)
            UserProfile.objects.get_or_create(user=u, defaults={"user_type": "student", "target_role": "Default"})
            return u

        with patch.object(User.objects, "create_user", side_effect=fake_create_user):
            response = self.client.post(self.register_url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            created_user = User.objects.get(username="signaluser")
            self.assertEqual(created_user.profile.user_type, "job_seeker")
            self.assertEqual(created_user.profile.target_role, "Cloud Architect")

    def test_register_case_insensitive_duplicate_email(self):
        payload = {
            "first_name": "Case",
            "last_name": "Insensitive",
            "username": "caseuser",
            "email": "EXISTING@EXAMPLE.COM",  # Registered as existing@example.com
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_case_insensitive_email(self):
        payload = {
            "username": "EXISTING@EXAMPLE.COM",  # Registered as existing@example.com
            "password": "ExistingPassword123",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertEqual(response.data["user"]["username"], "existinguser")

    def test_auth_me_invalid_bearer_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid.malformed.token")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_me_expired_token(self):
        token = RefreshToken.for_user(self.user).access_token
        token.set_exp(lifetime=-timedelta(minutes=10))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ResumeAPITests(APITestCase):
    """
    Test suite for Resume REST endpoints:
    - GET /api/v1/resumes/
    - POST /api/v1/resumes/
    - GET /api/v1/resumes/<id>/
    - DELETE /api/v1/resumes/<id>/
    """

    def setUp(self):
        self.resumes_url = reverse("api_v1:resume_list_create")

        # Create two distinct test users for ownership isolation testing
        self.user_a = User.objects.create_user(
            username="candidate_a",
            email="candidate_a@example.com",
            password="PasswordA123",
        )
        self.user_b = User.objects.create_user(
            username="candidate_b",
            email="candidate_b@example.com",
            password="PasswordB123",
        )

        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

    @patch("interviewapp.services.resume_service.index_resume")
    def test_resume_upload_success_file(self, mock_index):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        test_file = SimpleUploadedFile(
            "alice_resume.txt",
            b"Alice Smith - Senior Python & Django Engineer with 7 years experience.",
            content_type="text/plain",
        )
        response = self.client.post(
            self.resumes_url,
            {"title": "Alice Primary Resume", "file": test_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["title"], "Alice Primary Resume")
        self.assertTrue(response.data["file_name"].startswith("alice_resume"))
        self.assertTrue(response.data["file_name"].endswith(".txt"))
        self.assertTrue(response.data["has_file"])
        self.assertGreater(response.data["text_length"], 0)
        # Ensure private vector/internal fields are NOT exposed
        self.assertNotIn("vector_ids", response.data)
        self.assertNotIn("extracted_text", response.data)

        # Verify DB association and clean up file
        resume = Resume.objects.get(id=response.data["id"])
        self.assertEqual(resume.user, self.user_a)
        if resume.original_file:
            try:
                resume.original_file.delete(save=False)
            except Exception:
                pass

    @patch("interviewapp.services.resume_service.index_resume")
    def test_resume_upload_success_raw_text(self, mock_index):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            self.resumes_url,
            {"title": "Pasted Resume", "raw_text": "Experienced software architect specialized in distributed systems."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Pasted Resume")
        self.assertFalse(response.data["has_file"])

    def test_resume_upload_invalid_extension(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        bad_file = SimpleUploadedFile("malicious.exe", b"MZexecutablebytes", content_type="application/octet-stream")
        response = self.client.post(
            self.resumes_url,
            {"title": "Bad File", "file": bad_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    @patch("interviewapp.services.resume_service.index_resume")
    def test_resume_upload_oversized_file(self, mock_index):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        # Create a real file payload exceeding 10 MB (10 * 1024 * 1024 + 1 bytes)
        big_content = b"0" * (10 * 1024 * 1024 + 1)
        big_file = SimpleUploadedFile(
            "large_resume.pdf",
            big_content,
            content_type="application/pdf",
        )

        response = self.client.post(
            self.resumes_url,
            {"title": "Oversized File", "file": big_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_resume_upload_empty_payload(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(self.resumes_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resume_unauthenticated_access(self):
        response = self.client.get(self.resumes_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_resume_ownership_isolation(self):
        # User A owns Resume A
        resume_a = Resume.objects.create(
            user=self.user_a,
            title="Resume of Candidate A",
            extracted_text="Confidential details of Candidate A.",
        )
        detail_url = reverse("api_v1:resume_detail", kwargs={"pk": resume_a.id})

        # User B attempts to access User A's resume detail -> 404 (prevents enumeration)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        response_get = self.client.get(detail_url)
        self.assertEqual(response_get.status_code, status.HTTP_404_NOT_FOUND)

        # User B attempts to delete User A's resume -> 404
        response_delete = self.client.delete(detail_url)
        self.assertEqual(response_delete.status_code, status.HTTP_404_NOT_FOUND)

        # Verify resume still exists in database
        self.assertTrue(Resume.objects.filter(id=resume_a.id).exists())

    def test_resume_listing_and_deletion(self):
        # Create resumes for User A and User B
        resume_a1 = Resume.objects.create(user=self.user_a, title="User A Resume 1", extracted_text="Text 1")
        resume_a2 = Resume.objects.create(user=self.user_a, title="User A Resume 2", extracted_text="Text 2")
        resume_b1 = Resume.objects.create(user=self.user_b, title="User B Resume", extracted_text="Text B")

        # User A requests their resumes
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response_list = self.client.get(self.resumes_url)
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)
        returned_ids = [item["id"] for item in response_list.data]
        self.assertIn(resume_a1.id, returned_ids)
        self.assertIn(resume_a2.id, returned_ids)
        self.assertNotIn(resume_b1.id, returned_ids)

        # User A retrieves single resume detail
        detail_url = reverse("api_v1:resume_detail", kwargs={"pk": resume_a1.id})
        response_detail = self.client.get(detail_url)
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(response_detail.data["title"], "User A Resume 1")
        self.assertEqual(response_detail.data["text_length"], len("Text 1"))

        # User A deletes resume_a1
        with self.captureOnCommitCallbacks(execute=True):
            response_delete = self.client.delete(detail_url)
        self.assertEqual(response_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Resume.objects.filter(id=resume_a1.id).exists())

        # Second delete or get returns 404
        response_get_after = self.client.get(detail_url)
        self.assertEqual(response_get_after.status_code, status.HTTP_404_NOT_FOUND)

    def test_resume_upload_invalid_pdf_content(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        fake_pdf = SimpleUploadedFile("resume.pdf", b"NOT_A_VALID_PDF_HEADER_BYTES", content_type="application/pdf")
        response = self.client.post(
            self.resumes_url,
            {"title": "Fake PDF", "file": fake_pdf},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    @patch("interviewapp.services.resume_service.index_resume")
    def test_resume_upload_valid_pdf_header(self, mock_index):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        valid_pdf = SimpleUploadedFile(
            "valid_resume.pdf",
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            content_type="application/pdf",
        )
        with patch("interviewapp.services.resume_service.extract_text_from_resume_file", return_value="Extracted PDF text"):
            response = self.client.post(
                self.resumes_url,
                {"title": "Valid PDF", "file": valid_pdf},
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["title"], "Valid PDF")
            self.assertTrue(response.data["has_file"])

            # Clean up file
            resume = Resume.objects.get(id=response.data["id"])
            if resume.original_file:
                try:
                    resume.original_file.delete(save=False)
                except Exception:
                    pass

    def test_resume_upload_file_pointer_reset_after_validation(self):
        file_obj = SimpleUploadedFile("test.pdf", b"%PDF-1.4\nSome text content", content_type="application/pdf")
        serializer = ResumeUploadSerializer(data={"title": "Test", "file": file_obj})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        validated_file = serializer.validated_data["file"]
        self.assertEqual(validated_file.tell(), 0)

    def test_resume_deletion_removes_own_vector_store(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(RAG_INDEX_DIR=Path(temp_dir)):
                resume = Resume.objects.create(
                    user=self.user_a,
                    title="Resume with Vector Store",
                    extracted_text="Content for vector store.",
                )
                vec_dir = Path(temp_dir) / "resumes" / f"resume_{resume.id}"
                vec_dir.mkdir(parents=True, exist_ok=True)
                dummy_vec_file = vec_dir / "store_metadata.json"
                dummy_vec_file.write_text('{"collection": "test"}', encoding="utf-8")
                self.assertTrue(vec_dir.exists())

                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
                detail_url = reverse("api_v1:resume_detail", kwargs={"pk": resume.id})
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.delete(detail_url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(Resume.objects.filter(id=resume.id).exists())
                self.assertFalse(vec_dir.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_resume_deletion_preserves_other_vector_stores(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(RAG_INDEX_DIR=Path(temp_dir)):
                resume_a = Resume.objects.create(user=self.user_a, title="Resume A", extracted_text="Text A")
                resume_b = Resume.objects.create(user=self.user_a, title="Resume B", extracted_text="Text B")

                dir_a = Path(temp_dir) / "resumes" / f"resume_{resume_a.id}"
                dir_b = Path(temp_dir) / "resumes" / f"resume_{resume_b.id}"
                dir_a.mkdir(parents=True, exist_ok=True)
                dir_b.mkdir(parents=True, exist_ok=True)
                (dir_a / "meta.json").write_text("{}", encoding="utf-8")
                (dir_b / "meta.json").write_text("{}", encoding="utf-8")

                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
                detail_url_a = reverse("api_v1:resume_detail", kwargs={"pk": resume_a.id})
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.delete(detail_url_a)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                # Resume A vector store deleted, Resume B preserved
                self.assertFalse(dir_a.exists())
                self.assertTrue(dir_b.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_resume_deletion_when_vector_index_already_missing(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(RAG_INDEX_DIR=Path(temp_dir)):
                resume = Resume.objects.create(
                    user=self.user_a,
                    title="Resume with No Index",
                    extracted_text="Content",
                )
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
                detail_url = reverse("api_v1:resume_detail", kwargs={"pk": resume.id})
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.delete(detail_url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(Resume.objects.filter(id=resume.id).exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_resume_deletion_removes_physical_file(self):
        test_file = SimpleUploadedFile(
            "delete_me.txt",
            b"Delete this file from disk on resume deletion.",
            content_type="text/plain",
        )
        resume = Resume.objects.create(
            user=self.user_a,
            title="Resume to Delete With File",
            original_file=test_file,
            extracted_text="Sample text",
        )
        file_storage = resume.original_file.storage
        file_name = resume.original_file.name
        self.assertTrue(file_storage.exists(file_name))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        detail_url = reverse("api_v1:resume_detail", kwargs={"pk": resume.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(file_storage.exists(file_name))


class ResumeDeletionAndValidationHardeningTests(APITestCase):
    """
    Test suite for Phase 4A deletion and validation hardening:
    - Vector cleanup returning False or raising exceptions
    - RAG unavailable behavior
    - Database deletion failure preserving physical files & vector indices
    - Asset cleanup failures after DB commit
    - Idempotent cleanup retries
    - Template workflow validation (invalid extensions, oversized files, invalid PDF)
    - Consistency across API and template upload paths
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="hardening_user",
            email="hardening@example.com",
            password="HardeningPassword123",
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.resumes_url = reverse("api_v1:resume_list_create")
        self.template_start_url = reverse("interviewapp:start_resume_jd_session")

    def test_vector_cleanup_returning_false(self):
        with patch("interviewapp.services.resume_service.delete_resume_vector_store", return_value=False):
            result = cleanup_resume_assets(resume_id=101)
            self.assertFalse(result["vector_cleaned"])
            self.assertFalse(result["all_cleaned"])
            self.assertTrue(any("returned False" in err for err in result["errors"]))

    def test_vector_cleanup_raising_exception(self):
        with patch("interviewapp.services.resume_service.delete_resume_vector_store", side_effect=RuntimeError("Disk write error")):
            result = cleanup_resume_assets(resume_id=102)
            self.assertFalse(result["vector_cleaned"])
            self.assertFalse(result["all_cleaned"])
            self.assertTrue(any("Disk write error" in err for err in result["errors"]))

    def test_rag_unavailable_during_deletion(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(RAG_INDEX_DIR=Path(temp_dir)):
                with patch("interviewapp.services.resume_service._rag_available", False):
                    # Scenario A: Vector index directory exists on disk -> cannot clean without RAG
                    vec_dir = Path(temp_dir) / "resumes" / "resume_103"
                    vec_dir.mkdir(parents=True, exist_ok=True)
                    (vec_dir / "meta.json").write_text("{}", encoding="utf-8")

                    result_a = cleanup_resume_assets(resume_id=103)
                    self.assertFalse(result_a["vector_cleaned"])
                    self.assertFalse(result_a["all_cleaned"])

                    # Scenario B: Vector index directory does not exist anyway -> cleaned is True
                    result_b = cleanup_resume_assets(resume_id=104)
                    self.assertTrue(result_b["vector_cleaned"])
                    self.assertTrue(result_b["all_cleaned"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_database_deletion_failure_preserves_physical_file_and_vector_index(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(RAG_INDEX_DIR=Path(temp_dir)):
                test_file = SimpleUploadedFile("preserve_me.txt", b"Preserve this content.", content_type="text/plain")
                resume = Resume.objects.create(
                    user=self.user,
                    title="Resume To Fail Deletion",
                    original_file=test_file,
                    extracted_text="Some text",
                )
                file_storage = resume.original_file.storage
                file_name = resume.original_file.name
                self.assertTrue(file_storage.exists(file_name))

                vec_dir = Path(temp_dir) / "resumes" / f"resume_{resume.id}"
                vec_dir.mkdir(parents=True, exist_ok=True)
                (vec_dir / "meta.json").write_text("{}", encoding="utf-8")
                self.assertTrue(vec_dir.exists())

                # Simulate database failure during delete()
                with patch.object(Resume, "delete", side_effect=OperationalError("Database is locked")):
                    with self.assertRaises(OperationalError):
                        delete_candidate_resume(resume)

                # Confirm atomic rollback preserved both physical file and vector index
                self.assertTrue(file_storage.exists(file_name))
                self.assertTrue(vec_dir.exists())
                self.assertTrue(Resume.objects.filter(id=resume.id).exists())

                # Cleanup test file
                if resume.original_file:
                    resume.original_file.delete(save=False)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_physical_file_cleanup_failure_after_database_commit(self):
        test_file = SimpleUploadedFile("locked_file.txt", b"Locked content", content_type="text/plain")
        resume = Resume.objects.create(
            user=self.user,
            title="Resume File Lock",
            original_file=test_file,
            extracted_text="Content",
        )
        resume_id = resume.id

        with patch("interviewapp.services.resume_service.delete_resume_vector_store", return_value=True):
            with patch.object(resume.original_file, "delete", side_effect=PermissionError("File locked")):
                # Deletion succeeds at database layer and executes on_commit cleanup
                with self.captureOnCommitCallbacks(execute=True):
                    success = delete_candidate_resume(resume)
                self.assertTrue(success)
                self.assertFalse(Resume.objects.filter(id=resume_id).exists())

    def test_vector_cleanup_failure_after_database_commit(self):
        resume = Resume.objects.create(
            user=self.user,
            title="Resume Vector Failure",
            extracted_text="Content",
        )
        resume_id = resume.id

        with patch("interviewapp.services.resume_service.delete_resume_vector_store", return_value=False):
            with self.captureOnCommitCallbacks(execute=True):
                success = delete_candidate_resume(resume)
            self.assertTrue(success)
            self.assertFalse(Resume.objects.filter(id=resume_id).exists())

    def test_cleanup_retry_succeeding(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(RAG_INDEX_DIR=Path(temp_dir)):
                resume_id = 999
                vec_dir = Path(temp_dir) / "resumes" / f"resume_{resume_id}"
                vec_dir.mkdir(parents=True, exist_ok=True)
                (vec_dir / "meta.json").write_text("{}", encoding="utf-8")

                # Run 1: Simulated temporary failure
                with patch("interviewapp.services.resume_service.delete_resume_vector_store", return_value=False):
                    res1 = cleanup_resume_assets(resume_id=resume_id)
                    self.assertFalse(res1["all_cleaned"])

                # Run 2: Idempotent retry succeeds
                res2 = cleanup_resume_assets(resume_id=resume_id)
                self.assertTrue(res2["all_cleaned"])
                self.assertFalse(vec_dir.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_extension_through_template_upload(self):
        self.client.force_login(self.user)
        bad_file = SimpleUploadedFile("malicious.exe", b"MZexecutable", content_type="application/octet-stream")
        response = self.client.post(
            self.template_start_url,
            {"resume_file": bad_file, "job_description": "Software engineer role."},
            follow=False,
        )
        # Should redirect back to start_session with error message
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("start", response.url)
        self.assertEqual(Resume.objects.count(), 0)

    def test_oversized_template_upload(self):
        self.client.force_login(self.user)
        big_content = b"0" * (10 * 1024 * 1024 + 1)
        big_file = SimpleUploadedFile("large_resume.txt", big_content, content_type="text/plain")
        response = self.client.post(
            self.template_start_url,
            {"resume_file": big_file, "job_description": "Software engineer role."},
            follow=False,
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("start", response.url)
        self.assertEqual(Resume.objects.count(), 0)

    @patch("interviewapp.services.resume_service.index_resume")
    def test_valid_and_invalid_pdf_through_both_upload_paths(self, mock_index):
        # 1. API Path - Valid PDF
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        valid_pdf = SimpleUploadedFile("good.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", content_type="application/pdf")
        with patch("interviewapp.services.resume_service.extract_text_from_resume_file", return_value="Good PDF Text"):
            resp_api_valid = self.client.post(
                self.resumes_url,
                {"title": "Valid API PDF", "file": valid_pdf},
                format="multipart",
            )
            self.assertEqual(resp_api_valid.status_code, status.HTTP_201_CREATED)

        # 2. API Path - Invalid PDF (missing %PDF header)
        invalid_pdf = SimpleUploadedFile("bad.pdf", b"NOT_A_PDF_STREAM", content_type="application/pdf")
        resp_api_invalid = self.client.post(
            self.resumes_url,
            {"title": "Invalid API PDF", "file": invalid_pdf},
            format="multipart",
        )
        self.assertEqual(resp_api_invalid.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Template Path - Invalid PDF (missing %PDF header)
        self.client.force_login(self.user)
        resp_tmpl_invalid = self.client.post(
            self.template_start_url,
            {"resume_file": invalid_pdf, "job_description": "Backend Developer"},
            follow=False,
        )
        self.assertEqual(resp_tmpl_invalid.status_code, status.HTTP_302_FOUND)
        self.assertIn("start", resp_tmpl_invalid.url)

        # 4. Template Path - Valid PDF
        valid_pdf_2 = SimpleUploadedFile("good2.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", content_type="application/pdf")
        with patch("interviewapp.services.resume_service.extract_text_from_resume_file", return_value="Good Template PDF"):
            with patch("interviewapp.services.session_service.generate_resume_jd_rag_questions", return_value=[]):
                resp_tmpl_valid = self.client.post(
                    self.template_start_url,
                    {"resume_file": valid_pdf_2, "job_description": "Backend Developer"},
                    follow=False,
                )
                self.assertEqual(resp_tmpl_valid.status_code, status.HTTP_302_FOUND)
                self.assertIn("next", resp_tmpl_valid.url)


class SessionAPITests(APITestCase):
    """
    Test suite for Phase 4B.1 Interview Session REST APIs:
    - GET /api/v1/sessions/
    - POST /api/v1/sessions/
    - POST /api/v1/sessions/resume-jd/
    - GET /api/v1/sessions/<id>/
    - GET /api/v1/sessions/<id>/next-question/
    """

    MOCK_QUESTIONS = [
        {"text": "Explain Python GIL.", "role": "tech", "difficulty": 3, "keywords": "gil,thread"},
        {"text": "Explain Django ORM.", "role": "tech", "difficulty": 3, "keywords": "orm,django"},
        {"text": "Explain REST architecture.", "role": "tech", "difficulty": 3, "keywords": "rest,http"},
    ]

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="candidate_session_a",
            email="session_a@example.com",
            password="PasswordA123",
        )
        self.user_b = User.objects.create_user(
            username="candidate_session_b",
            email="session_b@example.com",
            password="PasswordB123",
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        self.sessions_url = reverse("api_v1:session_list_create")
        self.resume_jd_url = reverse("api_v1:session_resume_jd_create")

    def test_session_endpoints_require_authentication(self):
        # 1. List sessions unauthenticated
        res = self.client.get(self.sessions_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Create standard session unauthenticated
        res = self.client.post(self.sessions_url, {"role": "tech"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 3. Create resume-jd session unauthenticated
        res = self.client.post(self.resume_jd_url, {"job_description": "Dev"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 4. Detail session unauthenticated
        detail_url = reverse("api_v1:session_detail", kwargs={"pk": 999})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 5. Next question unauthenticated
        next_url = reverse("api_v1:session_next_question", kwargs={"pk": 999})
        res = self.client.get(next_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("interviewapp.services.session_service.generate_questions_groq")
    @patch("interviewapp.services.session_service.generate_questions_with_rag")
    def test_standard_session_creation_success(self, mock_rag, mock_groq):
        mock_rag.return_value = self.MOCK_QUESTIONS
        mock_groq.return_value = self.MOCK_QUESTIONS

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        payload = {
            "role": "tech",
            "job_role": "Python Backend Engineer",
            "difficulty": 3,
            "n_questions": 3,
        }
        response = self.client.post(self.sessions_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("session", response.data)
        self.assertIn("created_questions", response.data)
        self.assertEqual(response.data["created_questions"], 3)

        session_data = response.data["session"]
        self.assertEqual(session_data["role"], "tech")
        self.assertEqual(session_data["job_role"], "Python Backend Engineer")
        self.assertEqual(session_data["difficulty"], 3)
        self.assertEqual(session_data["total_questions"], 3)
        self.assertFalse(session_data["completed"])
        self.assertFalse(session_data["has_resume"])

        # Verify DB records
        session = InterviewSession.objects.get(id=session_data["id"])
        self.assertEqual(session.user, self.user_a)
        self.assertEqual(session.answers.count(), 3)
        self.assertEqual(session.current_index, 1)

    @patch("interviewapp.services.session_service.generate_resume_jd_rag_questions")
    @patch("interviewapp.services.session_service.generate_resume_jd_questions_groq")
    def test_resume_jd_session_creation_with_existing_resume(self, mock_groq, mock_rag):
        mock_rag.return_value = self.MOCK_QUESTIONS
        mock_groq.return_value = self.MOCK_QUESTIONS

        resume_a = Resume.objects.create(
            user=self.user_a,
            title="Alice Primary Resume",
            extracted_text="Alice has 5 years Python and Django experience.",
        )
        initial_resume_count = Resume.objects.count()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        payload = {
            "resume_id": resume_a.id,
            "job_description": "Senior Backend Django Engineer responsible for APIs and PostgreSQL.",
            "difficulty": 4,
            "n_questions": 3,
        }
        response = self.client.post(self.resume_jd_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        session_data = response.data["session"]
        self.assertTrue(session_data["has_resume"])
        self.assertEqual(session_data["resume_id"], resume_a.id)
        self.assertEqual(session_data["difficulty"], 4)

        # Confirm no duplicate resume record was created
        self.assertEqual(Resume.objects.count(), initial_resume_count)

        # Verify DB record
        session = InterviewSession.objects.get(id=session_data["id"])
        self.assertEqual(session.user, self.user_a)
        self.assertEqual(session.resume, resume_a)

    @patch("interviewapp.services.resume_service.index_resume")
    @patch("interviewapp.services.session_service.generate_resume_jd_rag_questions")
    @patch("interviewapp.services.session_service.generate_resume_jd_questions_groq")
    def test_resume_jd_session_creation_with_new_uploaded_file(self, mock_groq, mock_rag, mock_index):
        mock_rag.return_value = self.MOCK_QUESTIONS
        mock_groq.return_value = self.MOCK_QUESTIONS

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        new_file = SimpleUploadedFile("new_resume.txt", b"Bob - Cloud DevOps Architect.", content_type="text/plain")

        response = self.client.post(
            self.resume_jd_url,
            {
                "resume_title": "New Uploaded Resume",
                "resume_file": new_file,
                "job_description": "DevOps Engineer with Kubernetes and Terraform.",
                "difficulty": 3,
                "n_questions": 3,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["session"]["has_resume"])
        self.assertEqual(response.data["session"]["resume_title"], "New Uploaded Resume")

        # Verify resume created and associated with User A
        created_resume = Resume.objects.get(id=response.data["session"]["resume_id"])
        self.assertEqual(created_resume.user, self.user_a)
        if created_resume.original_file:
            created_resume.original_file.delete(save=False)

    def test_resume_jd_session_creation_existing_resume_ownership(self):
        # User B owns Resume B
        resume_b = Resume.objects.create(
            user=self.user_b,
            title="Candidate B Resume",
            extracted_text="Confidential data for User B.",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        # User A attempts to create a session referencing User B's resume ID
        payload = {
            "resume_id": resume_b.id,
            "job_description": "Python Engineer role.",
        }
        response = self.client.post(self.resume_jd_url, payload, format="json")
        # Must return 404 to avoid ID enumeration
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(InterviewSession.objects.count(), 0)

    def test_session_creation_invalid_inputs(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # 1. Invalid role
        res1 = self.client.post(self.sessions_url, {"role": "invalid_role"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", res1.data)

        # 2. Invalid difficulty (>5)
        res2 = self.client.post(self.sessions_url, {"difficulty": 10}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("difficulty", res2.data)

        # 3. Invalid n_questions (<1)
        res3 = self.client.post(self.sessions_url, {"n_questions": 0}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("n_questions", res3.data)

        # 4. Resume-JD with neither resume nor job description
        res4 = self.client.post(self.resume_jd_url, {}, format="json")
        self.assertEqual(res4.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. Resume-JD with invalid file format (.exe)
        bad_file = SimpleUploadedFile("bad.exe", b"MZexecutable", content_type="application/octet-stream")
        res5 = self.client.post(self.resume_jd_url, {"resume_file": bad_file}, format="multipart")
        self.assertEqual(res5.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume_file", res5.data)

    def test_session_listing_isolation(self):
        session_a1 = InterviewSession.objects.create(user=self.user_a, role="tech", job_role="Dev A1", total_questions=3)
        session_a2 = InterviewSession.objects.create(user=self.user_a, role="hr", job_role="Dev A2", total_questions=3)
        session_b1 = InterviewSession.objects.create(user=self.user_b, role="tech", job_role="Dev B1", total_questions=3)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(self.sessions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_ids = [item["id"] for item in response.data]
        self.assertIn(session_a1.id, returned_ids)
        self.assertIn(session_a2.id, returned_ids)
        self.assertNotIn(session_b1.id, returned_ids)

    def test_session_detail_ownership(self):
        session_a = InterviewSession.objects.create(user=self.user_a, role="tech", job_role="Backend", total_questions=2)
        detail_url = reverse("api_v1:session_detail", kwargs={"pk": session_a.id})

        # User A accesses own session -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        res_a = self.client.get(detail_url)
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(res_a.data["id"], session_a.id)
        self.assertEqual(res_a.data["job_role"], "Backend")

        # User B attempts to access User A's session -> 404 Not Found
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        res_b = self.client.get(detail_url)
        self.assertEqual(res_b.status_code, status.HTTP_404_NOT_FOUND)

    def test_next_question_retrieval_success(self):
        session_a = InterviewSession.objects.create(user=self.user_a, role="tech", job_role="Python", total_questions=2)
        q1 = GeneratedQuestion.objects.create(
            text="Explain generators in Python.",
            role="tech",
            difficulty=3,
            signature="gen_sig_1",
        )
        q2 = GeneratedQuestion.objects.create(
            text="Explain Python decorators.",
            role="tech",
            difficulty=3,
            signature="dec_sig_2",
        )
        Answer.objects.create(
            session=session_a,
            question=q1,
            index=1,
            processed=False,
            expected_answer="Generators use yield keyword to produce values lazily.",
        )
        Answer.objects.create(
            session=session_a,
            question=q2,
            index=2,
            processed=False,
            expected_answer="Decorators wrap functions using @ syntax.",
        )

        next_url = reverse("api_v1:session_next_question", kwargs={"pk": session_a.id})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(next_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_next_question"])
        self.assertEqual(response.data["current_index"], 1)
        self.assertEqual(response.data["total_questions"], 2)

        q_data = response.data["question"]
        self.assertEqual(q_data["id"], q1.id)
        self.assertEqual(q_data["text"], "Explain generators in Python.")
        self.assertEqual(q_data["role"], "tech")

        # CRITICAL SECURITY ASSERTIONS: answer key / internal data must NEVER be exposed
        self.assertNotIn("expected_answer", q_data)
        self.assertNotIn("signature", q_data)
        self.assertNotIn("score", response.data)
        self.assertNotIn("feedback", response.data)
        self.assertNotIn("expected_answer", response.data)

    def test_next_question_no_remaining_questions_and_completed_session(self):
        session_a = InterviewSession.objects.create(
            user=self.user_a,
            role="tech",
            job_role="Python",
            total_questions=1,
            completed=True,
        )
        q = GeneratedQuestion.objects.create(text="What is PEP 8?", role="tech", difficulty=1)
        Answer.objects.create(
            session=session_a,
            question=q,
            index=1,
            processed=True,
            score=90,
            feedback="Good",
        )

        next_url = reverse("api_v1:session_next_question", kwargs={"pk": session_a.id})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(next_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["has_next_question"])
        self.assertTrue(response.data["is_completed"])
        self.assertIn("No remaining questions", response.data["message"])

    def test_next_question_ownership(self):
        session_a = InterviewSession.objects.create(user=self.user_a, role="tech", job_role="Dev", total_questions=1)
        next_url = reverse("api_v1:session_next_question", kwargs={"pk": session_a.id})

        # User B attempts to get next question for User A's session -> 404
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        response = self.client.get(next_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_controlled_ai_service_failure(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        payload = {"role": "tech", "job_role": "Backend Engineer"}

        with patch("interviewapp.api.views.session_views.create_standard_session", side_effect=RuntimeError("Groq API rate limit exceeded")):
            response = self.client.post(self.sessions_url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn("detail", response.data)
            self.assertEqual(response.data["detail"], "Failed to initialize interview session. Please try again later.")
            self.assertNotIn("Groq API rate limit exceeded", response.data["detail"])

    def test_standard_session_creation_rollback_on_failure(self):
        """
        Verify that if question population fails unexpectedly,
        the newly created InterviewSession is completely rolled back from the database
        and the API returns a generic 500 error without leaking details.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        payload = {"role": "tech", "job_role": "Backend Engineer"}

        with patch("interviewapp.services.session_service.populate_session_questions", side_effect=RuntimeError("Database allocation failed")):
            response = self.client.post(self.sessions_url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data["detail"], "Failed to initialize interview session. Please try again later.")
            self.assertNotIn("Database allocation failed", response.data["detail"])

        # Confirm no InterviewSession was created or left orphaned
        self.assertFalse(InterviewSession.objects.filter(user=self.user_a).exists())

    def test_next_question_repeated_get_idempotency(self):
        """
        Verify that repeated GET requests to next-question return the exact same unanswered question
        idempotently, without advancing the session index or mutating answered state.
        """
        session = InterviewSession.objects.create(user=self.user_a, role="tech", job_role="Python", total_questions=2)
        q1 = GeneratedQuestion.objects.create(text="Question 1", role="tech", difficulty=3, signature="sig_idem_1")
        q2 = GeneratedQuestion.objects.create(text="Question 2", role="tech", difficulty=3, signature="sig_idem_2")
        ans1 = Answer.objects.create(session=session, question=q1, index=1, processed=False)
        ans2 = Answer.objects.create(session=session, question=q2, index=2, processed=False)

        next_url = reverse("api_v1:session_next_question", kwargs={"pk": session.id})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Call GET multiple times
        res1 = self.client.get(next_url)
        res2 = self.client.get(next_url)
        res3 = self.client.get(next_url)

        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res3.status_code, status.HTTP_200_OK)

        self.assertEqual(res1.data["answer_id"], ans1.id)
        self.assertEqual(res2.data["answer_id"], ans1.id)
        self.assertEqual(res3.data["answer_id"], ans1.id)

        self.assertEqual(res1.data["question"]["id"], q1.id)
        self.assertEqual(res2.data["question"]["id"], q1.id)
        self.assertEqual(res3.data["question"]["id"], q1.id)

        # Confirm session current_index remains 1 and neither answer is marked processed
        session.refresh_from_db()
        self.assertEqual(session.current_index, 1)
        self.assertEqual(session.answers.filter(processed=False).count(), 2)

    def test_safe_api_error_response_no_exception_leak(self):
        """
        Verify that 500 error responses from both session endpoints
        return user-friendly messages and never leak internal stack traces or database errors.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Standard session
        with patch("interviewapp.api.views.session_views.create_standard_session", side_effect=RuntimeError("SECRET_DB_CONN_STRING_LEAK")):
            res_std = self.client.post(self.sessions_url, {"role": "tech", "job_role": "Dev"}, format="json")
            self.assertEqual(res_std.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(res_std.data["detail"], "Failed to initialize interview session. Please try again later.")
            self.assertNotIn("SECRET_DB_CONN_STRING_LEAK", res_std.data["detail"])

        # Resume/JD session
        with patch("interviewapp.api.views.session_views.create_resume_jd_session", side_effect=RuntimeError("SECRET_VECTOR_STORE_PASSWORD")):
            res_rjd = self.client.post(self.resume_jd_url, {"job_description": "Some JD"}, format="json")
            self.assertEqual(res_rjd.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(res_rjd.data["detail"], "Failed to initialize resume-tailored session. Please try again later.")
            self.assertNotIn("SECRET_VECTOR_STORE_PASSWORD", res_rjd.data["detail"])

    @patch("interviewapp.services.resume_service.index_resume")
    def test_resume_jd_session_creation_failure_cleans_new_resume(self, mock_index):
        """
        When a new resume is uploaded during resume/JD session creation,
        if session initialization fails, the newly created resume must be cleaned up
        (both DB record and physical file) so no orphaned resume remains.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        new_file = SimpleUploadedFile("temp_resume.txt", b"Temporary Candidate Profile", content_type="text/plain")

        initial_resume_count = Resume.objects.count()

        with patch("interviewapp.services.session_service.populate_session_questions", side_effect=RuntimeError("Simulated allocation crash")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    self.resume_jd_url,
                    {
                        "resume_title": "Temp Resume",
                        "resume_file": new_file,
                        "job_description": "Software Engineer JD",
                    },
                    format="multipart",
                )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["detail"], "Failed to initialize resume-tailored session. Please try again later.")

        # Confirm session rolled back
        self.assertFalse(InterviewSession.objects.filter(user=self.user_a).exists())

        # Confirm newly created resume was cleaned up and deleted from DB
        self.assertEqual(Resume.objects.count(), initial_resume_count)

    def test_resume_jd_session_creation_failure_preserves_existing_resume(self):
        """
        When an existing resume_id is used for session creation,
        if session initialization fails, the existing resume must NOT be deleted.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        existing_resume = Resume.objects.create(
            user=self.user_a,
            title="Existing Permanent Resume",
            extracted_text="Existing resume text that must be kept safe.",
        )

        with patch("interviewapp.services.session_service.populate_session_questions", side_effect=RuntimeError("Simulated allocation crash")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    self.resume_jd_url,
                    {
                        "resume_id": existing_resume.id,
                        "job_description": "Software Engineer JD",
                    },
                    format="json",
                )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["detail"], "Failed to initialize resume-tailored session. Please try again later.")

        # Confirm session rolled back
        self.assertFalse(InterviewSession.objects.filter(user=self.user_a).exists())

        # CRITICAL ASSERTION: Existing resume must STILL exist in database
        self.assertTrue(Resume.objects.filter(id=existing_resume.id).exists())

    @patch("interviewapp.services.session_service.generate_questions_groq")
    def test_template_workflow_regression(self, mock_groq):
        mock_groq.return_value = self.MOCK_QUESTIONS

        self.client.force_login(self.user_a)
        start_url = reverse("interviewapp:start_session")

        # Submit valid template form
        response = self.client.post(
            start_url,
            {
                "role": "tech",
                "job_role": "Site Reliability Engineer",
                "difficulty": "3",
                "n_questions": 3,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("session", response.url)
        self.assertIn("next", response.url)

        # Verify session was created in DB for user_a
        created_session = InterviewSession.objects.filter(user=self.user_a, job_role="Site Reliability Engineer").first()
        self.assertIsNotNone(created_session)
        self.assertEqual(created_session.total_questions, 3)


class AnswerAndCompletionAPITests(APITestCase):
    """
    Test suite for Phase 4B.2 REST APIs:
    - POST /api/v1/sessions/<id>/answers/ (text and audio answers)
    - POST /api/v1/sessions/<id>/skip/ (skip question)
    - POST /api/v1/sessions/<id>/end/ (end session manually)
    - GET /api/v1/sessions/<id>/summary/ (performance summary)
    - GET /api/v1/sessions/<id>/report/ (PDF report download)
    - Authentication and cross-user ownership isolation
    - Audio format and size validation
    - Duplicate submission and completed session restrictions
    - AI / Whisper failure handling and safe file cleanup
    - Template workflow regression
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="candidate_a",
            email="candidate_a@example.com",
            password="StrongPassword123!",
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)

        self.user_b = User.objects.create_user(
            username="candidate_b",
            email="candidate_b@example.com",
            password="StrongPassword123!",
        )
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        # Create a standard 2-question session for User A
        self.session = InterviewSession.objects.create(
            user=self.user_a,
            role="tech",
            job_role="Senior Python Engineer",
            difficulty=3,
            total_questions=2,
            current_index=1,
        )
        self.q1 = GeneratedQuestion.objects.create(
            text="Explain GIL in CPython.",
            role="tech",
            difficulty=3,
            signature="gil_sig_1",
            keywords="gil,cpython,threads,lock",
        )
        self.q2 = GeneratedQuestion.objects.create(
            text="Explain asyncio event loop.",
            role="tech",
            difficulty=3,
            signature="async_sig_2",
            keywords="asyncio,event,loop,coroutines",
        )
        self.ans1 = Answer.objects.create(
            session=self.session,
            question=self.q1,
            index=1,
            processed=False,
            expected_answer="The GIL is a mutex that protects access to Python objects.",
        )
        self.ans2 = Answer.objects.create(
            session=self.session,
            question=self.q2,
            index=2,
            processed=False,
            expected_answer="The event loop manages and distributes the execution of tasks.",
        )

        self.answers_url = reverse("api_v1:session_answer_submit", kwargs={"pk": self.session.id})
        self.skip_url = reverse("api_v1:session_question_skip", kwargs={"pk": self.session.id})
        self.end_url = reverse("api_v1:session_end", kwargs={"pk": self.session.id})
        self.summary_url = reverse("api_v1:session_summary", kwargs={"pk": self.session.id})
        self.report_url = reverse("api_v1:session_report_download", kwargs={"pk": self.session.id})

    def tearDown(self):
        for ans in Answer.objects.filter(session=self.session):
            if ans.audio_file and hasattr(ans.audio_file, "name") and ans.audio_file.name:
                try:
                    storage = ans.audio_file.storage
                    if storage.exists(ans.audio_file.name):
                        storage.delete(ans.audio_file.name)
                except Exception:
                    pass

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_text_answer_submission_success(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 85.0,
            "feedback": "Strong explanation of the CPython GIL.",
            "improvement_tips": ["Mention CPU-bound vs I/O-bound concurrency."],
            "resume_grounding": None,
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        payload = {"answer_text": "The GIL ensures only one thread executes Python bytecode at a time."}

        response = self.client.post(self.answers_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Answer submitted and evaluated successfully.")
        self.assertFalse(response.data["is_session_completed"])

        ans_data = response.data["answer"]
        self.assertEqual(ans_data["id"], self.ans1.id)
        self.assertEqual(ans_data["score"], 85.0)
        self.assertEqual(ans_data["feedback"], "Strong explanation of the CPython GIL.")
        self.assertTrue(ans_data["processed"])
        self.assertNotIn("expected_answer", ans_data)

        # Next question should be Q2
        next_q = response.data["next_question"]
        self.assertIsNotNone(next_q)
        self.assertEqual(next_q["id"], self.q2.id)
        self.assertEqual(next_q["text"], "Explain asyncio event loop.")
        self.assertNotIn("expected_answer", next_q)

        # Confirm DB state
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.score, 85.0)

    @patch("interviewapp.services.answer_service.transcribe_audio")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_audio_answer_submission_with_transcription(self, mock_analyze, mock_transcribe):
        mock_transcribe.return_value = "The GIL allows only a single native thread to hold the Python interpreter lock."
        mock_analyze.return_value = {
            "score": 90.0,
            "feedback": "Clear voice explanation.",
            "improvement_tips": ["Good articulation."],
            "resume_grounding": None,
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        audio_file = SimpleUploadedFile("answer.wav", b"RIFFsamplewavdata", content_type="audio/wav")

        response = self.client.post(self.answers_url, {"audio_file": audio_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"]["score"], 90.0)
        self.assertEqual(
            response.data["answer"]["answer_text"],
            "The GIL allows only a single native thread to hold the Python interpreter lock.",
        )
        self.assertTrue(response.data["answer"]["has_audio"])

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_resume_grounded_evaluation_persistence(self, mock_analyze):
        resume = Resume.objects.create(
            user=self.user_a,
            title="Senior Architect Resume",
            extracted_text="Built microservices in Docker and Kubernetes.",
        )
        self.session.resume = resume
        self.session.job_description = "Kubernetes Architect role."
        self.session.save()

        grounding_data = {
            "consistency_score": 19,
            "alignment_level": "high",
            "supported_claims": ["Built microservices in Docker and Kubernetes."],
            "contradictions": [],
            "missed_resume_points": [],
        }
        mock_analyze.return_value = {
            "score": 95.0,
            "feedback": "Answers verified against candidate's verified resume claims.",
            "improvement_tips": ["Continue providing grounded metrics."],
            "resume_grounding": grounding_data,
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            self.answers_url,
            {"answer_text": "I managed production Kubernetes clusters."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ans_data = response.data["answer"]
        self.assertEqual(ans_data["resume_grounding"]["consistency_score"], 19)
        self.assertEqual(ans_data["resume_grounding"]["alignment_level"], "high")

        # Verify DB persistence
        self.ans1.refresh_from_db()
        self.assertEqual(self.ans1.resume_grounding["consistency_score"], 19)

    def test_skip_question(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(self.skip_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Question skipped successfully.")
        self.assertFalse(response.data["is_session_completed"])

        ans_data = response.data["answer"]
        self.assertEqual(ans_data["id"], self.ans1.id)
        self.assertEqual(ans_data["score"], 0)
        self.assertEqual(ans_data["answer_text"], "[Skipped]")
        self.assertEqual(ans_data["feedback"], "Question was skipped.")
        self.assertTrue(ans_data["processed"])

        # Next question should be Q2
        self.assertEqual(response.data["next_question"]["id"], self.q2.id)

        # Confirm DB state
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.score, 0)

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_session_completion_on_final_question(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 80.0,
            "feedback": "Good response.",
            "improvement_tips": [],
            "resume_grounding": None,
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Answer question 1
        res1 = self.client.post(self.answers_url, {"answer_text": "Answer 1"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertFalse(res1.data["is_session_completed"])

        # Answer question 2 (final)
        res2 = self.client.post(self.answers_url, {"answer_text": "Answer 2"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data["is_session_completed"])
        self.assertIsNone(res2.data["next_question"])

        # Verify DB session is completed
        self.session.refresh_from_db()
        self.assertTrue(self.session.completed)
        self.assertIsNotNone(self.session.completed_at)

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_duplicate_submission_protection(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 80.0,
            "feedback": "Good.",
            "improvement_tips": [],
            "resume_grounding": None,
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Submit answer to Q1
        res1 = self.client.post(
            self.answers_url,
            {"answer_id": self.ans1.id, "answer_text": "First attempt"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Retry submitting answer to Q1
        res2 = self.client.post(
            self.answers_url,
            {"answer_id": self.ans1.id, "answer_text": "Second attempt"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been answered and processed", res2.data["detail"])

        # Attempt to skip already answered Q1
        res_skip = self.client.post(self.skip_url, {"answer_id": self.ans1.id}, format="json")
        self.assertEqual(res_skip.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been answered or skipped", res_skip.data["detail"])

    def test_completed_session_restrictions(self):
        self.session.completed = True
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Cannot submit answer to completed session
        res_ans = self.client.post(self.answers_url, {"answer_text": "Late answer"}, format="json")
        self.assertEqual(res_ans.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been completed", res_ans.data["detail"])

        # Cannot skip question in completed session
        res_skip = self.client.post(self.skip_url, {}, format="json")
        self.assertEqual(res_skip.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been completed", res_skip.data["detail"])

    def test_audio_validation_invalid_and_oversized(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # 1. Invalid extension (.exe)
        bad_file = SimpleUploadedFile("malicious.exe", b"MZbadcode", content_type="application/octet-stream")
        res1 = self.client.post(self.answers_url, {"audio_file": bad_file}, format="multipart")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("audio_file", res1.data)
        self.assertTrue(any("Unsupported audio format" in str(err) for err in res1.data["audio_file"]))

        # 2. Oversized audio (> 25MB)
        large_bytes = b"0" * (25 * 1024 * 1024 + 1)
        large_file = SimpleUploadedFile("huge.mp3", large_bytes, content_type="audio/mpeg")
        res2 = self.client.post(self.answers_url, {"audio_file": large_file}, format="multipart")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("audio_file", res2.data)
        self.assertTrue(any("exceeds maximum limit" in str(err) for err in res2.data["audio_file"]))

        # 3. Neither text nor audio
        res3 = self.client.post(self.answers_url, {}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interviewapp.services.answer_service.transcribe_audio", side_effect=RuntimeError("Whisper CUDA error"))
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_ai_transcription_failure_handling(self, mock_analyze, mock_transcribe):
        mock_analyze.return_value = {
            "score": 0,
            "feedback": "Could not transcribe audio.",
            "improvement_tips": ["Check microphone settings."],
            "resume_grounding": None,
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        audio_file = SimpleUploadedFile("voice.mp3", b"ID3samplemp3data", content_type="audio/mpeg")

        response = self.client.post(self.answers_url, {"audio_file": audio_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"]["answer_text"], "[Voice answer could not be transcribed]")

    @patch("interviewapp.services.answer_service.analyze_transcript", side_effect=RuntimeError("Unexpected NLP crash"))
    def test_evaluation_failure_cleans_up_audio_file(self, mock_analyze):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        audio_file = SimpleUploadedFile("clean_me.wav", b"RIFFaudio_payload", content_type="audio/wav")

        response = self.client.post(self.answers_url, {"audio_file": audio_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["detail"], "Failed to process answer submission. Please try again later.")
        self.assertNotIn("Unexpected NLP crash", response.data["detail"])

        # Confirm answer remains unprocessed and no audio file remains attached
        self.ans1.refresh_from_db()
        self.assertFalse(self.ans1.processed)
        self.assertFalse(bool(self.ans1.audio_file))

    def test_end_session_manually(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(self.end_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Interview session ended successfully.")
        self.assertTrue(response.data["session"]["completed"])

        self.session.refresh_from_db()
        self.assertTrue(self.session.completed)
        self.assertIsNotNone(self.session.completed_at)

    def test_session_summary_retrieval(self):
        # Answer Q1 with score 80 and skip Q2
        self.ans1.answer_text = "Good answer to GIL"
        self.ans1.score = 80.0
        self.ans1.feedback = "Good explanation"
        self.ans1.processed = True
        self.ans1.save()

        self.ans2.answer_text = "[Skipped]"
        self.ans2.score = 0.0
        self.ans2.feedback = "Question was skipped."
        self.ans2.processed = True
        self.ans2.save()

        self.session.completed = True
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["average_score"], 40.0)
        self.assertEqual(response.data["completion_rate"], 50)
        self.assertIn("strengths", response.data)
        self.assertIn("improvements", response.data)
        self.assertIn("overall_tip", response.data)
        self.assertEqual(len(response.data["answers"]), 2)

        # In summary, expected answers are populated for study purposes
        self.assertIsNotNone(response.data["answers"][0]["expected_answer"])

    def test_pdf_report_download(self):
        self.ans1.score = 85.0
        self.ans1.processed = True
        self.ans1.save()
        self.session.completed = True
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(f"AI_Interview_Report_{self.session.id}.pdf", response["Content-Disposition"])
        self.assertGreater(len(response.content), 500)

    def test_authentication_and_ownership_enforcement(self):
        endpoints = [
            ("post", self.answers_url, {"answer_text": "Test"}),
            ("post", self.skip_url, {}),
            ("post", self.end_url, {}),
            ("get", self.summary_url, {}),
            ("get", self.report_url, {}),
        ]

        # 1. Unauthenticated requests -> 401 Unauthorized
        for method, url, data in endpoints:
            if method == "post":
                res = self.client.post(url, data, format="json")
            else:
                res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. User B requests User A's session -> 404 Not Found (object isolation)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        for method, url, data in endpoints:
            if method == "post":
                res = self.client.post(url, data, format="json")
            else:
                res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_template_workflow_regression(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 75.0,
            "feedback": "Satisfactory.",
            "improvement_tips": [],
            "resume_grounding": None,
        }

        self.client.force_login(self.user_a)

        # 1. Template submit answer
        submit_url = reverse("interviewapp:submit_answer", kwargs={"session_id": self.session.id})
        res_submit = self.client.post(
            submit_url,
            {"answer_id": self.ans1.id, "answer_text": "Template answer text"},
            follow=False,
        )
        self.assertEqual(res_submit.status_code, status.HTTP_302_FOUND)
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.claim_token, "")
        self.assertIsNone(self.ans1.claimed_at)

        # 2. Template skip question
        skip_url = reverse("interviewapp:skip_question", kwargs={"session_id": self.session.id})
        res_skip = self.client.post(skip_url, follow=False)
        self.assertEqual(res_skip.status_code, status.HTTP_302_FOUND)
        self.ans2.refresh_from_db()
        self.assertTrue(self.ans2.processed)
        self.assertEqual(self.ans2.processing_state, "processed")
        self.assertEqual(self.ans2.claim_token, "")
        self.assertIsNone(self.ans2.claimed_at)

        # 3. Template summary
        summary_url = reverse("interviewapp:session_summary", kwargs={"session_id": self.session.id})
        res_summary = self.client.get(summary_url)
        self.assertEqual(res_summary.status_code, status.HTTP_200_OK)

        # 4. Template download report
        report_url = reverse("interviewapp:download_report", kwargs={"session_id": self.session.id})
        res_report = self.client.get(report_url)
        self.assertEqual(res_report.status_code, status.HTTP_200_OK)
        self.assertEqual(res_report["Content-Type"], "application/pdf")

    def test_active_session_summary_returns_400(self):
        """Active sessions cannot access summary or leak expected answers."""
        self.session.completed = False
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Session performance summary is only available after interview completion.",
        )

    def test_active_session_pdf_report_returns_400(self):
        """Active sessions cannot generate or download performance PDF reports."""
        self.session.completed = False
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Interview report can only be downloaded after session completion.",
        )

    def test_future_question_submission_rejected(self):
        """Candidates cannot submit a future question out of order."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        # Q1 is unanswered; attempt to submit Q2
        payload = {"answer_id": self.ans2.id, "answer_text": "Out of order answer"}
        response = self.client.post(self.answers_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Questions must be answered in sequential order.")

        # Confirm neither question was processed
        self.ans1.refresh_from_db()
        self.ans2.refresh_from_db()
        self.assertFalse(self.ans1.processed)
        self.assertFalse(self.ans2.processed)

    def test_future_question_skip_rejected(self):
        """Candidates cannot skip a future question out of order."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        # Q1 is unanswered; attempt to skip Q2
        payload = {"answer_id": self.ans2.id}
        response = self.client.post(self.skip_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Questions must be answered in sequential order.")

        # Confirm neither question was processed
        self.ans1.refresh_from_db()
        self.ans2.refresh_from_db()
        self.assertFalse(self.ans1.processed)
        self.assertFalse(self.ans2.processed)

    def test_answer_id_from_another_session_rejected(self):
        """Submitting or skipping an answer ID from another session must return 400."""
        other_session = InterviewSession.objects.create(
            user=self.user_a,
            role="hr",
            job_role="HR Generalist",
            total_questions=1,
        )
        other_q = GeneratedQuestion.objects.create(text="HR Q", role="hr", difficulty=1)
        other_ans = Answer.objects.create(session=other_session, question=other_q, index=1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Post other session's answer_id to self.answers_url
        res1 = self.client.post(self.answers_url, {"answer_id": other_ans.id, "answer_text": "Test"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res1.data["detail"], "Answer not found in this session.")

        # Post other session's answer_id to self.skip_url
        res2 = self.client.post(self.skip_url, {"answer_id": other_ans.id}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.data["detail"], "Answer not found in this session.")

    def test_concurrent_and_service_level_protection(self):
        """Service layer rejects processing already completed answers."""
        from interviewapp.services.answer_service import (
            AnswerAlreadyProcessedError,
            submit_candidate_answer,
        )

        self.ans1.processed = True
        self.ans1.score = 90.0
        self.ans1.save()

        # Calling submit_candidate_answer on already processed answer must raise AnswerAlreadyProcessedError (a ValueError)
        with self.assertRaises(AnswerAlreadyProcessedError) as ctx:
            submit_candidate_answer(self.session, self.ans1.id, answer_text="Late text")
        self.assertIn("already been processed", str(ctx.exception))

    def test_atomic_claim_only_one_request_wins(self):
        """
        Verify acquire_answer_claim() grants an exclusive UUID token to the first caller
        and immediately rejects a second caller while the claim is active.
        """
        from interviewapp.services.answer_service import (
            AnswerCurrentlyProcessingError,
            acquire_answer_claim,
        )

        token1 = acquire_answer_claim(self.session, self.ans1.id)
        self.assertTrue(bool(token1))
        self.assertEqual(len(token1), 32)

        self.ans1.refresh_from_db()
        self.assertEqual(self.ans1.processing_state, "processing")
        self.assertEqual(self.ans1.claim_token, token1)
        self.assertIsNotNone(self.ans1.claimed_at)
        self.assertFalse(self.ans1.processed)

        # Second request attempting to claim the same answer must fail immediately
        with self.assertRaises(AnswerCurrentlyProcessingError):
            acquire_answer_claim(self.session, self.ans1.id)

        # Token of the winning claim remains untouched
        self.ans1.refresh_from_db()
        self.assertEqual(self.ans1.claim_token, token1)

    @patch("interviewapp.services.answer_service.transcribe_audio")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_duplicate_request_rejected_before_ai_inference_and_cannot_overwrite_text_or_audio(
        self, mock_analyze, mock_transcribe
    ):
        """
        Simulate a second concurrent API request arriving while the first request is inside
        AI evaluation:
        - Only one request executes Whisper/Groq inference.
        - The losing request is rejected with HTTP 409 Conflict before AI inference.
        - The losing request cannot overwrite answer_text or audio_file.
        - The winning request's audio remains attached and its text/score are committed.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        losing_responses = []

        def side_effect_analyze(text, question, resume=None, job_description=""):
            # While the winning request is in-flight during AI inference,
            # a duplicate request arrives with different text and a different audio file
            losing_audio = SimpleUploadedFile(
                "losing.wav", b"RIFFlosing_audio_bytes", content_type="audio/wav"
            )
            losing_res = self.client.post(
                self.answers_url,
                {
                    "answer_id": self.ans1.id,
                    "answer_text": "Losing concurrent text that must NEVER be saved",
                    "audio_file": losing_audio,
                },
                format="multipart",
            )
            losing_responses.append(losing_res)
            return {
                "score": 92.0,
                "feedback": "Winning evaluation feedback.",
                "improvement_tips": ["Great concurrency handling."],
                "resume_grounding": None,
            }

        mock_transcribe.return_value = "Winning transcribed audio answer."
        mock_analyze.side_effect = side_effect_analyze

        winning_audio = SimpleUploadedFile(
            "winning.wav", b"RIFFwinning_audio_bytes", content_type="audio/wav"
        )
        winning_res = self.client.post(
            self.answers_url,
            {
                "answer_id": self.ans1.id,
                "audio_file": winning_audio,
            },
            format="multipart",
        )

        # 1. Winning request succeeds with HTTP 200
        self.assertEqual(winning_res.status_code, status.HTTP_200_OK)
        # 2. Losing in-flight request was rejected with HTTP 409 Conflict
        self.assertEqual(len(losing_responses), 1)
        self.assertEqual(losing_responses[0].status_code, status.HTTP_409_CONFLICT)
        self.assertIn("currently being processed", losing_responses[0].data["detail"])

        # 3. AI inference and Whisper transcription ran ONLY ONCE (for the winner)
        self.assertEqual(mock_analyze.call_count, 1)
        self.assertEqual(mock_transcribe.call_count, 1)

        # 4. Winning answer_text, score, and audio_file are committed; losing data never overwrote them
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.claim_token, "")
        self.assertIsNone(self.ans1.claimed_at)
        self.assertEqual(self.ans1.answer_text, "Winning transcribed audio answer.")
        self.assertEqual(self.ans1.score, 92.0)
        self.assertTrue(bool(self.ans1.audio_file and self.ans1.audio_file.name))
        self.assertTrue(self.ans1.audio_file.storage.exists(self.ans1.audio_file.name))

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_claim_ownership_verification_aborts_commit_if_token_lost(self, mock_analyze):
        """
        Verify that if a worker's claim_token is replaced before final commit
        (e.g., because the worker stalled past timeout and another worker took over),
        the stale worker's final commit is rejected (AnswerClaimLostError -> HTTP 409),
        its temporary audio file is deleted, and the newer state in the DB is untouched.
        """
        storage = self.ans1.audio_file.storage
        newer_audio_rel_path = storage.save(
            f"voice_answers/ans_{self.ans1.id}_newerwinner.wav",
            SimpleUploadedFile("newer.wav", b"RIFFnewer", content_type="audio/wav"),
        )
        self.addCleanup(
            lambda: storage.delete(newer_audio_rel_path)
            if storage.exists(newer_audio_rel_path)
            else None
        )

        def simulate_claim_takeover(text, question, resume=None, job_description=""):
            # Simulate another worker reclaiming and completing the answer while this worker was running
            Answer.objects.filter(id=self.ans1.id).update(
                answer_text="Committed by newer worker",
                audio_file=newer_audio_rel_path,
                score=96.0,
                feedback="Newer worker feedback",
                processed=True,
                processing_state="processed",
                claim_token="",
                claimed_at=None,
            )
            return {
                "score": 10.0,
                "feedback": "Stale worker feedback that must be discarded",
                "improvement_tips": [],
                "resume_grounding": None,
            }

        mock_analyze.side_effect = simulate_claim_takeover

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        stale_audio = SimpleUploadedFile("stale.wav", b"RIFFstale", content_type="audio/wav")
        response = self.client.post(
            self.answers_url,
            {
                "answer_id": self.ans1.id,
                "answer_text": "Stale worker text",
                "audio_file": stale_audio,
            },
            format="multipart",
        )

        # Stale worker receives HTTP 409 Conflict because its claim token was no longer valid at commit
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        # Newer worker's committed answer text, score, and audio file remain intact!
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.answer_text, "Committed by newer worker")
        self.assertEqual(self.ans1.score, 96.0)
        self.assertEqual(self.ans1.audio_file.name, newer_audio_rel_path)
        self.assertTrue(storage.exists(newer_audio_rel_path))

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_failed_evaluation_releases_claim_to_failed_and_retry_succeeds(self, mock_analyze):
        """
        Verify that when AI evaluation raises an exception:
        1. The claim transitions to processing_state='failed', claim_token='', claimed_at=None.
        2. The temporary audio file created by the failed request is deleted.
        3. A subsequent retry request can reclaim the failed answer and succeed.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # First attempt fails during AI evaluation
        mock_analyze.side_effect = RuntimeError("Temporary Groq outage")
        failed_audio = SimpleUploadedFile("fail_attempt.wav", b"RIFFfail", content_type="audio/wav")
        res1 = self.client.post(
            self.answers_url,
            {"answer_id": self.ans1.id, "answer_text": "First try", "audio_file": failed_audio},
            format="multipart",
        )
        self.assertEqual(res1.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.ans1.refresh_from_db()
        self.assertFalse(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "failed")
        self.assertEqual(self.ans1.claim_token, "")
        self.assertIsNone(self.ans1.claimed_at)
        self.assertEqual(self.ans1.answer_text, "")
        self.assertFalse(bool(self.ans1.audio_file))

        # Second attempt (retry) succeeds
        mock_analyze.side_effect = None
        mock_analyze.return_value = {
            "score": 88.0,
            "feedback": "Succeeded on retry.",
            "improvement_tips": ["Keep going."],
            "resume_grounding": None,
        }
        retry_audio = SimpleUploadedFile("retry_attempt.wav", b"RIFFretry", content_type="audio/wav")
        res2 = self.client.post(
            self.answers_url,
            {"answer_id": self.ans1.id, "answer_text": "Retry text", "audio_file": retry_audio},
            format="multipart",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.claim_token, "")
        self.assertIsNone(self.ans1.claimed_at)
        self.assertEqual(self.ans1.answer_text, "Retry text")
        self.assertEqual(self.ans1.score, 88.0)
        self.assertTrue(bool(self.ans1.audio_file and self.ans1.audio_file.name))

    @override_settings(ANSWER_CLAIM_TIMEOUT_SECONDS=60)
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_stale_claim_recovery_and_token_protection(self, mock_analyze):
        """
        Verify that an Answer stuck in 'processing' with claimed_at older than
        ANSWER_CLAIM_TIMEOUT_SECONDS can be reclaimed by a new request, and that
        release_answer_claim_on_failure() with the old stale token cannot release
        the new worker's claim.
        """
        from django.utils import timezone
        from interviewapp.services.answer_service import (
            acquire_answer_claim,
            release_answer_claim_on_failure,
        )

        stale_time = timezone.now() - timedelta(seconds=120)
        Answer.objects.filter(id=self.ans1.id).update(
            processing_state="processing",
            claim_token="stale_dead_worker_token_11111111",
            claimed_at=stale_time,
            processed=False,
        )

        # New worker reclaims the stale answer
        new_token = acquire_answer_claim(self.session, self.ans1.id)
        self.assertNotEqual(new_token, "stale_dead_worker_token_11111111")

        # Stale worker waking up and attempting to release its old token must be a no-op
        released = release_answer_claim_on_failure(
            self.ans1.id, "stale_dead_worker_token_11111111"
        )
        self.assertFalse(released)

        # New worker's claim remains active and intact
        self.ans1.refresh_from_db()
        self.assertEqual(self.ans1.processing_state, "processing")
        self.assertEqual(self.ans1.claim_token, new_token)

        # Release the new claim so we can also test full end-to-end API recovery from a stale state
        Answer.objects.filter(id=self.ans1.id).update(
            processing_state="processing",
            claim_token="stale_dead_worker_token_22222222",
            claimed_at=stale_time,
            processed=False,
        )
        mock_analyze.return_value = {
            "score": 84.0,
            "feedback": "Recovered from stale claim.",
            "improvement_tips": [],
            "resume_grounding": None,
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            self.answers_url,
            {"answer_id": self.ans1.id, "answer_text": "Recovered answer"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.score, 84.0)

    @patch("interviewapp.services.answer_service.transcribe_audio")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_long_running_claim_renewal_and_lost_claim_abort_after_transcription(
        self, mock_analyze, mock_transcribe
    ):
        """
        Verify long-running claim behavior:
        1. Normal audio flow calls renew_answer_claim() after Whisper transcription, refreshing claimed_at.
        2. If the claim was lost during a slow transcription, submit_candidate_answer() aborts
           immediately after transcription without calling analyze_transcript() and cleans up its audio.
        """
        from interviewapp.services import answer_service

        # Case 1: Verify renew_answer_claim is called during audio submission
        with patch(
            "interviewapp.services.answer_service.renew_answer_claim",
            wraps=answer_service.renew_answer_claim,
        ) as spy_renew:
            mock_transcribe.return_value = "Transcribed voice response"
            mock_analyze.return_value = {
                "score": 91.0,
                "feedback": "Good voice answer.",
                "improvement_tips": [],
                "resume_grounding": None,
            }
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
            audio1 = SimpleUploadedFile("voice1.wav", b"RIFFvoice1", content_type="audio/wav")
            res1 = self.client.post(
                self.answers_url,
                {"answer_id": self.ans1.id, "audio_file": audio1},
                format="multipart",
            )
            self.assertEqual(res1.status_code, status.HTTP_200_OK)
            self.assertEqual(spy_renew.call_count, 1)

        # Case 2: On Q2, simulate claim lost during slow Whisper transcription
        mock_analyze.reset_mock()

        def slow_transcribe_losing_claim(path):
            # Another worker takes over ans2 while Whisper is running
            Answer.objects.filter(id=self.ans2.id).update(
                processing_state="processing",
                claim_token="other_worker_token_9999",
            )
            return "Late transcription"

        mock_transcribe.side_effect = slow_transcribe_losing_claim
        audio2 = SimpleUploadedFile("voice2.wav", b"RIFFvoice2", content_type="audio/wav")
        res2 = self.client.post(
            self.answers_url,
            {"answer_id": self.ans2.id, "audio_file": audio2},
            format="multipart",
        )
        self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)
        # Groq evaluation (analyze_transcript) must NOT have been called after claim renewal failed
        self.assertEqual(mock_analyze.call_count, 0)

    def test_sqlite_lock_retry_behavior(self):
        """
        Verify _run_with_sqlite_lock_retry():
        1. Retries transient SQLite 'database is locked' errors and succeeds when the lock clears.
        2. Raises AnswerDatabaseContentionError when transient lock retries are exhausted (API returns 503).
        3. Does NOT retry non-lock OperationalErrors (e.g., syntax/schema error).
        """
        from interviewapp.services.answer_service import (
            AnswerDatabaseContentionError,
            _run_with_sqlite_lock_retry,
        )

        # 1. Transient lock succeeds on 3rd attempt
        attempts = {"count": 0}

        def flaky_db_op():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise OperationalError("database is locked")
            return "committed"

        result = _run_with_sqlite_lock_retry(flaky_db_op, max_retries=3, base_delay=0.001)
        self.assertEqual(result, "committed")
        self.assertEqual(attempts["count"], 3)

        # 2. Exhausted lock retries raise AnswerDatabaseContentionError
        with self.assertRaises(AnswerDatabaseContentionError):
            _run_with_sqlite_lock_retry(
                lambda: (_ for _ in ()).throw(OperationalError("database is locked")),
                max_retries=2,
                base_delay=0.001,
            )

        # 3. Non-lock OperationalError is re-raised immediately without retries
        non_lock_attempts = {"count": 0}

        def bad_sql_op():
            non_lock_attempts["count"] += 1
            raise OperationalError("no such column: interviewapp_answer.nonexistent")

        with self.assertRaises(OperationalError):
            _run_with_sqlite_lock_retry(bad_sql_op, max_retries=3, base_delay=0.001)
        self.assertEqual(non_lock_attempts["count"], 1)

        # 4. API view returns controlled HTTP 503 Service Unavailable on AnswerDatabaseContentionError
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        with patch(
            "interviewapp.api.views.session_views.submit_candidate_answer",
            side_effect=AnswerDatabaseContentionError("Database is temporarily busy"),
        ):
            res_api = self.client.post(
                self.answers_url,
                {"answer_text": "Contention test"},
                format="json",
            )
            self.assertEqual(res_api.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertIn("temporarily busy", res_api.data["detail"])

    def test_skip_versus_processing_contention(self):
        """
        Verify skip contention behavior:
        1. An Answer with an active 'processing' claim cannot be skipped (returns HTTP 409 Conflict).
        2. An Answer with a stale/expired 'processing' claim or 'failed' state CAN be skipped atomically.
        """
        from django.utils import timezone
        from interviewapp.services.answer_service import acquire_answer_claim

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # 1. Acquire active claim on ans1
        token = acquire_answer_claim(self.session, self.ans1.id)
        res_skip_active = self.client.post(
            self.skip_url,
            {"answer_id": self.ans1.id},
            format="json",
        )
        self.assertEqual(res_skip_active.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("currently being processed", res_skip_active.data["detail"])

        # Confirm ans1 is still processing with its token intact
        self.ans1.refresh_from_db()
        self.assertFalse(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processing")
        self.assertEqual(self.ans1.claim_token, token)

        # 2. Age the claim past timeout -> skip now succeeds atomically
        Answer.objects.filter(id=self.ans1.id).update(
            claimed_at=timezone.now() - timedelta(seconds=300)
        )
        res_skip_stale = self.client.post(
            self.skip_url,
            {"answer_id": self.ans1.id},
            format="json",
        )
        self.assertEqual(res_skip_stale.status_code, status.HTTP_200_OK)
        self.ans1.refresh_from_db()
        self.assertTrue(self.ans1.processed)
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.claim_token, "")
        self.assertIsNone(self.ans1.claimed_at)
        self.assertEqual(self.ans1.answer_text, "[Skipped]")
        self.assertEqual(self.ans1.score, 0)

    def test_migration_processing_state_initialization(self):
        """
        Verify that the migration helper initializes existing Answer records consistently:
        - processed=True -> processing_state='processed'
        - processed=False -> processing_state='unclaimed'
        """
        from django.apps import apps
        from importlib import import_module

        migration_mod = import_module("interviewapp.migrations.0005_answer_claim_fields")

        # Simulate pre-migration state via queryset update
        Answer.objects.filter(id=self.ans1.id).update(
            processed=True,
            processing_state="unclaimed",
            claim_token="leftover",
        )
        Answer.objects.filter(id=self.ans2.id).update(
            processed=False,
            processing_state="processing",
            claim_token="leftover",
        )

        migration_mod.initialize_answer_processing_state(apps, None)

        self.ans1.refresh_from_db()
        self.ans2.refresh_from_db()
        self.assertEqual(self.ans1.processing_state, "processed")
        self.assertEqual(self.ans1.claim_token, "")
        self.assertEqual(self.ans2.processing_state, "unclaimed")
        self.assertEqual(self.ans2.claim_token, "")






