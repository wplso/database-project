# **시작하기 전 준비물**

이 프로젝트를 실행하기 위해서는 아래 프로그램들이 컴퓨터에 설치되어 있어야 합니다.

1. **Python (3.10 버전 이상)**: 설치 시 Add Python to PATH 체크박스 필수 선택.  
2. **MySQL Server & Workbench**: 설치 시 설정한 root 비밀번호 필요.  
3. **Git**: https://github.com/wplso/database-project  
4. **VS Code (Visual Studio Code)**

# **설치 및 환경 설정 (Installation)**

### **1\. Git에서 프로젝트 다운로드**

### **2\. 가상환경 생성 및 활성화 (Backend)**

**Windows:**

python \-m venv dbproject  
source dbproject/Scripts/activate    
\# 또는 .\\dbproject\\Scripts\\activate

(터미널 앞부분에 (dbproject)라고 뜨면 성공입니다.)

### **3\. 필수 라이브러리 설치**

프로젝트 실행에 필요한 도구들을 한 번에 설치합니다.

pip install \-r requirements.txt

### **4\. 데이터베이스 설정**

MySQL Workbench를 실행하고 로컬 인스턴스에 접속합니다.

아래 SQL 명령어를 입력하고 번개 아이콘을 눌러 실행하여 빈 데이터베이스를 만듭니다.

CREATE DATABASE librarydb   
CHARACTER SET utf8mb4   
COLLATE utf8mb4\_unicode\_ci;

VS Code에서 bookBorrow/settings.py 파일을 엽니다.

DATABASES 항목을 찾아 PASSWORD 부분을 본인의 MySQL 비밀번호로 수정하고 저장합니다.

DATABASES \= {  
    'default': {  
        'ENGINE': 'django.db.backends.mysql',  
        'NAME': 'librarydb',  
        'USER': 'root',  
        'PASSWORD': '여기에\_본인\_비밀번호\_입력',   
        'HOST': '127.0.0.1',  
        'PORT': '3306',  
    }  
}

### **5\. 데이터베이스 테이블 생성 (Migration)**

장고가 데이터베이스에 테이블을 만들도록 명령합니다. (가상환경에서 실행)  
(manage.py 파일이 있는 디렉토리로 이동후 실행 해야 합니다. 명령어: cd .\\bookBorrow)  
python manage.py makemigrations  
python manage.py migrate

### **6\. 초기 데이터 구축 (Data Import)**

빈 데이터베이스에 카테고리, 출판사, 책 정보를 채워 넣습니다. 반드시 아래 순서대로 실행해주세요.

\# 1\. 카테고리 정보 입력  
python import\_categories.py

\# 2\. 출판사 정보 입력  
python import\_publisher.py

\# 3\. 도서 상세 정보(BookInfo) 입력 (시간이 조금 걸릴 수 있습니다)  
python import\_bookinfo.py

\# 4\. 실물 도서(Book) 재고 생성  
python import\_book.py

### **7\. 관리자 계정 생성**

관리자 페이지 접속 및 관리를 위한 슈퍼유저를 만듭니다.

python manage.py createsuperuser  
\# 아이디, 이메일, 비밀번호 등을 입력하세요.

# **프로젝트 실행 (Run)**

이 프로젝트는 백엔드 서버와 프론트엔드 화면을 동시에 실행해야 합니다.

### **1\. 백엔드 서버 실행 (Django)**

터미널에서 아래 명령어를 입력합니다.  
(manage.py 파일이 있는 디렉토리로 이동후 실행 해야 합니다. 명령어: cd .\\bookBorrow)  
python manage.py runserver

터미널에 Starting development server at http://127.0.0.1:8000/ 문구가 뜨면 성공입니다. 이 터미널은 끄지 말고 켜두세요.

### **2\. 프론트엔드 실행 (Live Server)**

1. VS Code 왼쪽 메뉴의 **확장(Extensions)** 아이콘을 클릭합니다.  
2. "Live Server"를 검색하여 설치합니다.  
3. 탐색기에서 Main.html (또는 Login.html) 파일을 우클릭합니다.  
4. "Open with Live Server"를 클릭합니다.  
5. 브라우저가 열리면서 웹사이트가 실행됩니다.

# **문제 해결 (Troubleshooting)**

**MySQL 연결 오류 (OperationalError):**

* MySQL 서버가 켜져 있는지 확인하세요.  
* settings.py의 비밀번호가 일치하는지 확인하세요.

**CORS 오류 (Network Error):**

* 백엔드 서버(runserver)가 켜져 있는지 확인하세요.  
* HTML 파일을 그냥 더블클릭해서 열지 말고 Live Server로 열어야 합니다.

# **만든 사람들 (Team 7\)**

* **팀원:** 이상오, 송창준, 최준성, 허재원  
* **소속:** 공주대학교 천안공과대학 컴퓨터공학과  
* **과목:** 데이터베이스설계
