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
* * **역할:**
  * 1. 이상오(팀장, Backend Main, DB 설계 보완)
    프로젝트 초기 기획을 주도하고, Django 기반의 백엔드 프레임워크 구축과 핵심 API 개발을 담당했습니다.
       · 기획 및 설계:
            · 초기 요구사항 상세 정의.
            · DB 모델링 심화: 개념/논리적 모델링 검토 및 수정(도서와 도서정보 테이블 분리 제안, VARCHAR/INT 타입 결정 등 정규화 및 무결성 제약조건 강화).
       · 개발(Backend & Frontend):
            · Backend:
                · Django 환경 구축: models.py 정의, import_*.py 작성, URL 연결, views.py 함수 작성 등 백엔드의 뼈대를 완성.
            · Frontend:
                · 내 정보 수정 기능 구현.
                · 관리자의 정책관리 기능 구현
                · 관리자의 도서 등록, 도서 정보 수정, 회원 등록, 회원의 대여관리, 회원 상세 정보, 회원 정보 수정 모달창의 디자인 수정
       · 문서화: 결과 보고서 최종 검토 및 수정, README.md 상세 작성.
  * 2. 최준성(PM 역할, Data 구축, 문서화, 기능 구현)
    일정 관리와 문서 정리를 전담하며, 도서 데이터를 수집·정제하고 관리자급 기능을 구현했습니다.
       · 기획 및 설계:
            · 개념적/논리적 모델링 진행 과정 정리 및 문서화(진행 과정 PDF 제작).
            · 물리적 모델링 초안 작성(MySQL) 및 피드백 반영.
       · 데이터 구축:
            · 국립중앙도서관 데이터셋(약 14만 건) 수집 및 Python(pandas)을 이용한 전처리(정제), DB 적재.
       · 개발(Backend & Frontend):
            · Frontend:
                · 리뷰 관리 시스템: 리뷰 작성/수정 UI 개선, 금지어 필터링(로컬 스토리지 활용), 정렬 기능 구현.
                · 회원 관리 시스템: 관리자용 회원 목록 조회, 검색, 대여/반납 처리 모달(Modal) 기능 구현.
                · 코드 오류 수정(URL/View 매칭 문제 해결).
            · Backend:
                · views.py 및 urls.py 수정
       · 문서화: 중간/최종 발표 PPT 작성, 결과 보고서 초안 작성 및 취합.
  * 3. 송창준(Frontend Main, 아이디어 제안)
    과거 경험을 바탕으로 주제를 제안하고, 프론트엔드 개발을 전담하여 전체적인 웹 디자인과 구조를 잡고, 메인 로직을 구현했습니다.
       · 기획 및 설계:
            · 도서 대여 시스템 주제 및 초기 프론트엔드 리소스 제공.
       · 개발(Backend & Frontend):
            · Frontend:
                · 전체 웹 애플리케이션의 UI/UX 레이아웃과 디자인 테마를 구축하고 초기 소스코드를 제공하여 프론트엔드의 뼈대를 완성.
                · 핵심 페이지 및 로직 구현: 메인 화면, 로그인, 회원가입 등 사용자가 가장 먼저 접하는 인터페이스와 로직을 전담하여 구현.
                · 코드 리팩토링 및 병합: 다른 팀원이 작업한 MyPage 등의 코드를 가져와 UI 스타일에 맞게 다듬고(Refactoring), 충돌(Conflict)을 해결하며 브랜치를 관리.
            · Backend:
                · views.py 및 urls.py 수정
       · Github 관리: 초기 Github 레포지토리 생성 및 브랜치(login 브랜치) 관리, 병합 충돌 해결 시도.
       · 문서화: Django 설치 및 실행 가이드(README) 초안 작성.
  * 4. 허재원(Tester, 발표, 보고서 및 발표자료 작성)
    구현된 시스템의 테스트를 담당하고, 밯표를 담당했습니다.
       · 기획 및 설계:
            · 팀 미팅 참여 및 요구사항 분석 단계에서 의견 조율.
       · 발표:
            · 중간 발표 담당: 팀을 대표하여 중간 진행 상황 발표.
            · 최종 발표 담당: 팀을 대표하여 최종 발표.
       · 테스트 및 문서화:
            · 시스템 테스트: 팀원들이 구현한 기능(관리자/회원 기능)을 로컬 환경에서 테스트하고 검증.
            · 보고서 작성: 결과 보고서의 '실행 화면' 파트 작성(스크린샷 및 기능 설명).
            · 최종 발표 자료: 최종 발표 PPT 수정 및 제출.

