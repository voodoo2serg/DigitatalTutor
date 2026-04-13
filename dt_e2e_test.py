#!/usr/bin/env python3
"""
E2E Testing Script for DigitalTutor
Tests all major functions via API
"""

import requests
import json
import sys
from datetime import datetime, timedelta

BASE_URL = "http://213.171.9.30:8000"
API_URL = f"{BASE_URL}/api/v1"
TEST_TELEGRAM_ID = 123456789

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_pass(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def log_fail(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def log_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def log_warn(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

class DTE2ETest:
    def __init__(self):
        self.user_id = None
        self.work_id = None
        self.file_id = None
        self.auth_code = None
        self.results = []
        
    def test_health(self):
        """Phase 0: Health check"""
        log_info("=== Phase 0: Health Check ===")
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=10)
            if r.status_code == 200 and r.json().get("status") == "healthy":
                log_pass("API is healthy")
                return True
            else:
                log_fail(f"Health check failed: {r.status_code}")
                return False
        except Exception as e:
            log_fail(f"Health check error: {e}")
            return False
    
    def test_registration(self):
        """Phase 1: User Registration"""
        log_info("=== Phase 1: Registration Flow ===")
        
        # Check if user exists
        try:
            r = requests.get(f"{API_URL}/users/by-telegram/{TEST_TELEGRAM_ID}", timeout=10)
            if r.status_code == 200:
                log_warn("User already exists, deleting...")
                # Delete user
                user_id = r.json().get("id")
                requests.delete(f"{API_URL}/users/{user_id}", timeout=10)
        except:
            pass
        
        # Create user
        user_data = {
            "telegram_id": TEST_TELEGRAM_ID,
            "telegram_username": "test_user",
            "full_name": "Иванов Иван Иванович",
            "role": "student",
            "group_name": "КС-101",
            "course": 4,
            "email": "test@example.com"
        }
        
        try:
            r = requests.post(f"{API_URL}/users/", json=user_data, timeout=10)
            if r.status_code == 201 or r.status_code == 200:
                resp = r.json()
                self.user_id = resp.get("id")
                log_pass(f"User created: {self.user_id}")
            else:
                log_fail(f"User creation failed: {r.status_code} - {r.text}")
                return False
        except Exception as e:
            log_fail(f"User creation error: {e}")
            return False
        
        # Verify user in DB
        try:
            r = requests.get(f"{API_URL}/users/{self.user_id}", timeout=10)
            if r.status_code == 200:
                user = r.json()
                if user.get("full_name") == "Иванов Иван Иванович":
                    log_pass("User data verified in DB")
                else:
                    log_fail("User data mismatch")
                    return False
            else:
                log_fail(f"User verification failed: {r.status_code}")
                return False
        except Exception as e:
            log_fail(f"User verification error: {e}")
            return False
        
        return True
    
    def test_work_creation(self):
        """Phase 2: Create Student Work"""
        log_info("=== Phase 2: Work Creation ===")
        
        # Get work types
        try:
            r = requests.get(f"{API_URL}/work-types/", timeout=10)
            work_types = r.json()
            if not work_types:
                log_fail("No work types available")
                return False
            work_type_id = work_types[0].get("id")
            log_pass(f"Found work type: {work_types[0].get('name')}")
        except Exception as e:
            log_fail(f"Work types error: {e}")
            return False
        
        # Create work
        deadline = (datetime.now() + timedelta(days=30)).isoformat()
        work_data = {
            "title": "Тестовая работа E2E",
            "description": "Описание тестовой работы для E2E тестирования",
            "work_type_id": work_type_id,
            "deadline": deadline
        }
        
        try:
            r = requests.post(
                f"{API_URL}/student-works/?telegram_id={TEST_TELEGRAM_ID}",
                json=work_data,
                timeout=10
            )
            if r.status_code == 201 or r.status_code == 200:
                resp = r.json()
                self.work_id = resp.get("id")
                log_pass(f"Work created: {self.work_id}")
            else:
                log_fail(f"Work creation failed: {r.status_code} - {r.text}")
                return False
        except Exception as e:
            log_fail(f"Work creation error: {e}")
            return False
        
        return True
    
    def test_file_upload(self):
        """Phase 3: File Upload"""
        log_info("=== Phase 3: File Upload ===")
        
        # Create test file
        test_content = b"This is a test file for E2E testing"
        
        try:
            files = {
                'file': ('test_file.txt', test_content, 'text/plain')
            }
            data = {
                'work_id': self.work_id,
                'telegram_id': str(TEST_TELEGRAM_ID),
                'description': 'Test file upload'
            }
            
            r = requests.post(
                f"{API_URL}/files/upload/",
                files=files,
                data=data,
                timeout=30
            )
            
            if r.status_code == 201 or r.status_code == 200:
                resp = r.json()
                self.file_id = resp.get("id")
                log_pass(f"File uploaded: {self.file_id}")
            else:
                log_fail(f"File upload failed: {r.status_code} - {r.text}")
                return False
        except Exception as e:
            log_fail(f"File upload error: {e}")
            return False
        
        return True
    
    def test_ai_analysis(self):
        """Phase 4: AI Analysis"""
        log_info("=== Phase 4: AI Analysis ===")
        
        # Check Ollama connection
        try:
            r = requests.get("http://213.171.9.30:11434/api/tags", timeout=10)
            if r.status_code == 200:
                models = r.json().get("models", [])
                log_pass(f"Ollama connected, {len(models)} models available")
            else:
                log_warn("Ollama check failed, continuing...")
        except Exception as e:
            log_warn(f"Ollama connection error: {e}")
        
        # Create AI analysis log
        analysis_data = {
            "work_id": self.work_id,
            "provider": "ollama",
            "model": "gemma3:4b",
            "analysis_type": "structure_review",
            "prompt": "Test prompt",
            "response": "Test AI response",
            "tokens_used": 150,
            "execution_time_ms": 2500,
            "success": True
        }
        
        try:
            r = requests.post(
                f"{API_URL}/ai-analysis/",
                json=analysis_data,
                timeout=10
            )
            if r.status_code == 201 or r.status_code == 200:
                log_pass("AI analysis log created")
            else:
                log_fail(f"AI analysis failed: {r.status_code} - {r.text}")
                return False
        except Exception as e:
            log_fail(f"AI analysis error: {e}")
            return False
        
        return True
    
    def test_communication(self):
        """Phase 5: Communication"""
        log_info("=== Phase 5: Communication ===")
        
        # Create communication
        comm_data = {
            "student_id": self.user_id,
            "work_id": self.work_id,
            "from_user_id": self.user_id,
            "to_user_id": self.user_id,  # Self for test
            "message": "Тестовое сообщение от студента",
            "message_type": "text"
        }
        
        try:
            r = requests.post(
                f"{API_URL}/communications/",
                json=comm_data,
                timeout=10
            )
            if r.status_code == 201 or r.status_code == 200:
                log_pass("Communication message created")
            else:
                log_fail(f"Communication failed: {r.status_code} - {r.text}")
                return False
        except Exception as e:
            log_fail(f"Communication error: {e}")
            return False
        
        return True
    
    def test_web_auth(self):
        """Phase 6: Web Auth"""
        log_info("=== Phase 6: Web Interface ===")
        
        # Generate auth code
        try:
            r = requests.post(
                f"{API_URL}/web-auth/generate-code?telegram_id={TEST_TELEGRAM_ID}",
                timeout=10
            )
            if r.status_code == 200:
                resp = r.json()
                self.auth_code = resp.get("code")
                log_pass(f"Auth code generated: {self.auth_code}")
            else:
                log_fail(f"Auth code generation failed: {r.status_code}")
                return False
        except Exception as e:
            log_fail(f"Auth code error: {e}")
            return False
        
        # Verify auth code
        try:
            r = requests.post(
                f"{API_URL}/web-auth/verify-code",
                json={"code": self.auth_code},
                timeout=10
            )
            if r.status_code == 200:
                log_pass("Auth code verified")
            else:
                log_fail(f"Auth code verification failed: {r.status_code}")
                return False
        except Exception as e:
            log_fail(f"Auth verification error: {e}")
            return False
        
        # Check web interface
        try:
            r = requests.get(f"http://213.171.9.30:8098", timeout=10)
            if r.status_code == 200:
                log_pass("Web interface accessible")
            else:
                log_warn(f"Web interface status: {r.status_code}")
        except Exception as e:
            log_warn(f"Web interface error: {e}")
        
        return True
    
    def cleanup(self):
        """Cleanup test data"""
        log_info("=== Cleanup ===")
        try:
            if self.work_id:
                requests.delete(f"{API_URL}/student-works/{self.work_id}", timeout=10)
                log_pass("Work deleted")
            if self.user_id:
                requests.delete(f"{API_URL}/users/{self.user_id}", timeout=10)
                log_pass("User deleted")
        except Exception as e:
            log_warn(f"Cleanup error: {e}")
    
    def run_all(self):
        """Run all tests"""
        print("="*60)
        print("DIGITALTUTOR E2E TEST SUITE")
        print("="*60)
        
        start_time = datetime.now()
        
        tests = [
            ("Health Check", self.test_health),
            ("Registration", self.test_registration),
            ("Work Creation", self.test_work_creation),
            ("File Upload", self.test_file_upload),
            ("AI Analysis", self.test_ai_analysis),
            ("Communication", self.test_communication),
            ("Web Auth", self.test_web_auth),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    self.results.append((name, True, None))
                else:
                    failed += 1
                    self.results.append((name, False, "Test failed"))
            except Exception as e:
                failed += 1
                self.results.append((name, False, str(e)))
                log_fail(f"Exception in {name}: {e}")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Cleanup
        self.cleanup()
        
        # Report
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        
        for name, status, error in self.results:
            status_str = f"{Colors.GREEN}PASS{Colors.END}" if status else f"{Colors.RED}FAIL{Colors.END}"
            print(f"{name:<25} {status_str}")
            if error:
                print(f"  Error: {error}")
        
        print("-"*60)
        print(f"Total: {passed + failed} | {Colors.GREEN}Passed: {passed}{Colors.END} | {Colors.RED}Failed: {failed}{Colors.END}")
        print(f"Duration: {duration:.2f}s")
        print("="*60)
        
        return failed == 0

if __name__ == "__main__":
    tester = DTE2ETest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
