from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import unittest
import random
import string
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select

class LibrarySystemTest(unittest.TestCase):
    def setUp(self):
       
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-notifications')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.base_url = 'http://localhost:5000'
        self.driver.get(self.base_url)
        self.wait = WebDriverWait(self.driver, 10)
        
        
        self.test_username = self.generate_unique_username()
        self.test_email = self.generate_unique_email()
        self.test_password = "test123"

    def generate_unique_username(self):
        """Benzersiz kullanıcı adı oluştur"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"test_user_{random_suffix}"

    def generate_unique_email(self):
        """Benzersiz e-posta adresi oluştur"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"test_{random_suffix}@example.com"

    def generate_unique_isbn(self):
        """Benzersiz ISBN numarası oluştur"""
       
        isbn = ''.join(random.choices(string.digits, k=13))
        return isbn

    def wait_and_find_element(self, by, value, timeout=10):
        """Elementi bulana kadar bekle ve bulduğunda döndür"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            print(f"Element bulunamadı: {value}")
            return None

    def wait_and_click(self, by, value, timeout=10):
        """Elementi bulana kadar bekle ve tıklanabilir olduğunda tıkla"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            return True
        except TimeoutException:
            print(f"Element tıklanamadı: {value}")
            return False

    def login_as_admin(self):
        """Admin olarak giriş yap"""
        if not self.wait_and_click(By.LINK_TEXT, "Giriş"):
            self.fail("Giriş linki bulunamadı")
        
        username = self.wait_and_find_element(By.NAME, "username")
        password = self.wait_and_find_element(By.NAME, "password")
        
        if not all([username, password]):
            self.fail("Giriş formu alanları bulunamadı")
        
        username.send_keys("admin")
        password.send_keys("admin123")
        
        login_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
        if login_button:
            login_button.click()
            time.sleep(3)
        else:
            self.fail("Giriş yap butonu bulunamadı")

    def test_register_and_login(self):
        try:
            
            print("Kayıt olma işlemi başlıyor...")
            if not self.wait_and_click(By.LINK_TEXT, "Kayıt Ol"):
                self.fail("Kayıt Ol linki bulunamadı")
            
           
            username = self.wait_and_find_element(By.NAME, "username")
            email = self.wait_and_find_element(By.NAME, "email")
            password = self.wait_and_find_element(By.NAME, "password")
            
            if not all([username, email, password]):
                self.fail("Kayıt formu alanları bulunamadı")
            
            username.send_keys(self.test_username)
            email.send_keys(self.test_email)
            password.send_keys(self.test_password)
            
            
            register_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if register_button:
                register_button.click()
                time.sleep(2)
            else:
                self.fail("Kayıt ol butonu bulunamadı")
            
            
            print("Giriş yapma işlemi başlıyor...")
            username = self.wait_and_find_element(By.NAME, "username")
            password = self.wait_and_find_element(By.NAME, "password")
            
            if not all([username, password]):
                self.fail("Giriş formu alanları bulunamadı")
            
            username.send_keys(self.test_username)
            password.send_keys(self.test_password)
            
            login_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if login_button:
                login_button.click()
                time.sleep(2)
            else:
                self.fail("Giriş yap butonu bulunamadı")
            
           
            print("Giriş başarılı mı kontrol ediliyor...")
            books_link = self.wait_and_find_element(By.LINK_TEXT, "Kitaplar")
            if not books_link:
                
                error_messages = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
                if error_messages:
                    print(f"Giriş hatası: {error_messages[0].text}")
                self.fail("Giriş başarısız: Kitaplar linki bulunamadı")
            
            print("Giriş başarılı!")
            
        except Exception as e:
            print(f"Test sırasında hata oluştu: {str(e)}")
            self.fail(f"Test başarısız: {str(e)}")

    def test_book_operations(self):
        try:
          
            self.test_register_and_login()
            
            print("Kitap işlemleri testi başlıyor...")
           
            if not self.wait_and_click(By.LINK_TEXT, "Kitaplar"):
                self.fail("Kitaplar linki bulunamadı")
            
            time.sleep(3)
            
           
            search_input = self.wait_and_find_element(By.NAME, "search")
            if not search_input:
                self.fail("Arama kutusu bulunamadı")
            
            search_input.send_keys("Kar")
            search_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if search_button:
                search_button.click()
                time.sleep(3)
            else:
                self.fail("Arama butonu bulunamadı")
            
            
            try:
                
                book_link = self.wait_and_find_element(By.LINK_TEXT, "Kar")
                if not book_link:
                    
                    book_links = self.driver.find_elements(By.CSS_SELECTOR, "a.text-decoration-none.text-dark")
                    book_link = None
                    for link in book_links:
                        if "kar" in link.text.lower():
                            book_link = link
                            break
                
                if book_link:
                    book_link.click()
                    time.sleep(3)
                else:
                    self.fail("Kitap linki bulunamadı")
            except Exception as e:
                print(f"Kitap arama hatası: {str(e)}")
                self.fail("Kitap linki bulunamadı")
            
            
            borrow_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if borrow_button:
                borrow_button.click()
                time.sleep(3)
            else:
                self.fail("Ödünç alma butonu bulunamadı")
            
            print("Kitap işlemleri testi başarılı!")
            
        except Exception as e:
            print(f"Test sırasında hata oluştu: {str(e)}")
            self.fail(f"Test başarısız: {str(e)}")

    def test_profile_update(self):
        try:
            
            self.test_register_and_login()
            
            print("Profil güncelleme testi başlıyor...")
            
            if not self.wait_and_click(By.LINK_TEXT, "Profil"):
                self.fail("Profil linki bulunamadı")
            
            time.sleep(2)
            
            
            email_input = self.wait_and_find_element(By.NAME, "email")
            current_password = self.wait_and_find_element(By.NAME, "current_password")
            new_password = self.wait_and_find_element(By.NAME, "new_password")
            
            if not all([email_input, current_password, new_password]):
                self.fail("Profil formu alanları bulunamadı")
            
            
            new_email = self.generate_unique_email()
            email_input.clear()
            email_input.send_keys(new_email)
            current_password.send_keys(self.test_password)
            new_password.send_keys("newtest123")
            
            save_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if save_button:
                save_button.click()
                time.sleep(2)
            else:
                self.fail("Kaydet butonu bulunamadı")
            
            print("Profil güncelleme testi başarılı!")
            
        except Exception as e:
            print(f"Test sırasında hata oluştu: {str(e)}")
            self.fail(f"Test başarısız: {str(e)}")

    def test_admin_operations(self):
        """Admin işlemlerini test et"""
        print("Admin işlemleri testi başlıyor...")
        
        # Admin olarak giriş yap
        self.driver.get(f"{self.base_url}/login")
        username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_input = self.driver.find_element(By.NAME, "password")
        
        username_input.send_keys("admin")
        password_input.send_keys("admin123")
        password_input.send_keys(Keys.RETURN)
        
        time.sleep(2)  
        
        # Kitap ekleme sayfasına git
        self.driver.get(f"{self.base_url}/books/add")
        time.sleep(2) 
        
        # Rastgele bir kitap araması yap
        search_terms = ["Harry Potter", "Lord of the Rings", "Game of Thrones", "The Hobbit", 
                       "1984", "The Great Gatsby", "To Kill a Mockingbird", "Pride and Prejudice"]
        random_search = random.choice(search_terms)
        
        
        search_input = self.wait.until(EC.presence_of_element_located((By.ID, "searchInput")))
        search_button = self.driver.find_element(By.ID, "searchButton")
        
        search_input.send_keys(random_search)
        search_button.click()
        time.sleep(2)  
        
        
        try:
            results_list = self.wait.until(EC.presence_of_element_located((By.ID, "resultsList")))
            first_result = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "list-group-item")))
            first_result.click()
            time.sleep(2)  # Form alanlarının doldurulması için bekle
            
            
            title_input = self.wait.until(EC.presence_of_element_located((By.ID, "title")))
            isbn_input = self.driver.find_element(By.ID, "isbn")
            author_input = self.driver.find_element(By.ID, "author")
            category_select = self.driver.find_element(By.ID, "category_id")
            quantity_input = self.driver.find_element(By.ID, "quantity")
            
            
            unique_isbn = self.generate_unique_isbn()
            current_title = title_input.get_attribute("value")
            current_author = author_input.get_attribute("value")
            
            
            if not current_title:
                current_title = f"Test Kitabı {random.randint(1000, 9999)}"
            if not current_author:
                current_author = "Test Yazar"
            
            
            title_input.clear()
            title_input.send_keys(current_title)
            
            isbn_input.clear()
            isbn_input.send_keys(unique_isbn)
            
            author_input.clear()
            author_input.send_keys(current_author)
            
            
            Select(category_select).select_by_visible_text("Fantastik")
            
          
            quantity_input.clear()
            quantity_input.send_keys("5")
            
            # Sayfayı biraz aşağı kaydır
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  
            
            # Kaydet butonunu bul ve tıkla
            save_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
            time.sleep(1)  
            save_button.click()
            
            time.sleep(2)  
            
            
            success_message = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "alert-success")))
            self.assertIn("başarıyla", success_message.text.lower())
            
            print(f"Test kitabı başarıyla eklendi: {current_title} (ISBN: {unique_isbn})")
            
        except Exception as e:
            print(f"Admin işlemleri testi sırasında hata: {str(e)}")
            self.fail(f"Test başarısız: {str(e)}")

    def test_book_return(self):
        """Kitap iade işlemlerini test et"""
        try:
            print("Kitap iade testi başlıyor...")
          
            self.test_register_and_login()
            
           
            if not self.wait_and_click(By.LINK_TEXT, "Kitaplar"):
                self.fail("Kitaplar linki bulunamadı")
            
            time.sleep(3)
            
           
            search_input = self.wait_and_find_element(By.NAME, "search")
            if not search_input:
                self.fail("Arama kutusu bulunamadı")
            
            search_input.send_keys("Kar")
            search_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if search_button:
                search_button.click()
                time.sleep(3)
            else:
                self.fail("Arama butonu bulunamadı")
            
            # Kitap detaylarına git
            book_link = self.wait_and_find_element(By.LINK_TEXT, "Kar")
            if not book_link:
                book_links = self.driver.find_elements(By.CSS_SELECTOR, "a.text-decoration-none.text-dark")
                book_link = None
                for link in book_links:
                    if "kar" in link.text.lower():
                        book_link = link
                        break
            
            if book_link:
                book_link.click()
                time.sleep(3)
            else:
                self.fail("Kitap linki bulunamadı")
            
           
            borrow_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if borrow_button:
                borrow_button.click()
                time.sleep(3)
            else:
                self.fail("Ödünç alma butonu bulunamadı")
            
           
            if not self.wait_and_click(By.LINK_TEXT, "Ödünç Aldıklarım"):
                self.fail("Ödünç Aldıklarım linki bulunamadı")
            
            time.sleep(2)
            
            # İade butonunu bul ve tıkla
            return_button = self.wait_and_find_element(By.CSS_SELECTOR, "button.btn-sm.btn-success")
            if return_button:
                return_button.click()
                time.sleep(2)
                
                
                try:
                    alert = self.driver.switch_to.alert
                    alert.accept()  
                    time.sleep(2)
                except:
                    print("Onay penceresi bulunamadı")
                
               
                success_message = self.wait_and_find_element(By.CLASS_NAME, "alert-success")
                if not success_message:
                    self.fail("İade başarılı mesajı bulunamadı")
            else:
                self.fail("İade butonu bulunamadı")
            
            print("Kitap iade testi başarılı!")
            
        except Exception as e:
            print(f"Test sırasında hata oluştu: {str(e)}")
            self.fail(f"Test başarısız: {str(e)}")

    def test_error_cases(self):
        """Hata durumlarını test et"""
        try:
            print("Hata durumları testi başlıyor...")
            
            
            if not self.wait_and_click(By.LINK_TEXT, "Giriş"):
                self.fail("Giriş linki bulunamadı")
            
            username = self.wait_and_find_element(By.NAME, "username")
            password = self.wait_and_find_element(By.NAME, "password")
            
            if not all([username, password]):
                self.fail("Giriş formu alanları bulunamadı")
            
            username.send_keys("yanlis_kullanici")
            password.send_keys("yanlis_sifre")
            
            login_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if login_button:
                login_button.click()
                time.sleep(3)  
                
                
                error_messages = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
                if not error_messages:
                   
                    flash_messages = self.driver.find_elements(By.CLASS_NAME, "alert")
                    if not flash_messages:
                        self.fail("Hata mesajı bulunamadı")
            
           
            if not self.wait_and_click(By.LINK_TEXT, "Kayıt Ol"):
                self.fail("Kayıt Ol linki bulunamadı")
            
            username = self.wait_and_find_element(By.NAME, "username")
            email = self.wait_and_find_element(By.NAME, "email")
            password = self.wait_and_find_element(By.NAME, "password")
            
            if not all([username, email, password]):
                self.fail("Kayıt formu alanları bulunamadı")
            
            username.send_keys("admin")  
            email.send_keys(self.test_email)
            password.send_keys(self.test_password)
            
            register_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']")
            if register_button:
                register_button.click()
                time.sleep(3)  
                
                
                error_messages = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
                if not error_messages:
                    
                    flash_messages = self.driver.find_elements(By.CLASS_NAME, "alert")
                    if not flash_messages:
                        self.fail("Hata mesajı bulunamadı")
            
            print("Hata durumları testi başarılı!")
            
        except Exception as e:
            print(f"Test sırasında hata oluştu: {str(e)}")
            self.fail(f"Test başarısız: {str(e)}")

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main() 