import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import cv2
from PIL import Image
import os
import tempfile
import re
import shutil
import time
from dotenv import load_dotenv

# 새로 권장된 최신 표준 SDK 적용
from google import genai
from google.genai import types

load_dotenv()

# --- 페이지 설정 ---
st.set_page_config(
    page_title="MyKidMediaGuard", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 완벽한 폰트 및 모드 덮어쓰기 CSS
st.markdown("""
    <!-- PWA 메타 태그 (모바일 홈 화면 추가 시 앱처럼 독립 뷰포트 지원) -->
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="mobile-web-app-capable" content="yes">

    <style>
    /* 1. 최상위 @import 적용을 통한 프리미엄 Pretendard 폰트 강제 로드 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

    /* 2. 전체 테마 강제 적용: 완전한 블랙(#0E1117) 및 순백색(#FFFFFF) 텍스트 */
    html, body, [class*="css"], [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Pretendard', sans-serif !important;
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    
    /* 3. 새로운 카드 디자인 입체화 클래스 */
    .custom-card {
        background-color: #262730;
        border-radius: 15px;
        padding: 24px;
        border: 1px solid #464855;
        margin-bottom: 25px;
        color: #FFFFFF;
        box-shadow: 0 6px 12px rgba(0,0,0,0.4);
    }
    
    /* 4. 상태별 메인 팝업 카드 */
    .safe { color: #FFFFFF; font-weight: bold; font-size: 24px; padding: 22px; background-color: #262730; border: 2px solid #28a745; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);}
    .warning { color: #FFFFFF; font-weight: bold; font-size: 24px; padding: 22px; background-color: #262730; border: 2px solid #ffc107; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);}
    .block { color: #FFFFFF; font-weight: bold; font-size: 24px; padding: 22px; background-color: #262730; border: 2px solid #ff4b4b; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);}
    
    /* 5. 강조 텍스트 극대화 (황금색 배경에 검은 글씨 강제) */
    mark { 
        background-color: #FFD700 !important; 
        color: #000000 !important; 
        font-weight: 900 !important; 
        padding: 2px 6px;
        border-radius: 4px;
        text-shadow: none !important;
    }
    
    /* 6. 타이틀 및 헤더 사이즈 폭발적 확장 */
    h1 { font-size: 3.0rem !important; font-weight: 900 !important; margin-bottom: 0px !important; }
    h2 { font-size: 2.2rem !important; font-weight: 800 !important; }
    h3 { font-size: 1.8rem !important; font-weight: 800 !important; }
    
    /* 7. 하이브리드 UI 모바일 오버라이드 */
    @media (max-width: 768px) {
        .safe, .warning, .block, .custom-card { padding: 18px !important; }
        h1 { font-size: 2.2rem !important; }
        h2, h3 { font-size: 1.6rem !important; }
        div[data-testid="stButton"] button {
            height: 65px !important; 
            font-size: 24px !important; 
            font-weight: 900 !important; 
            border-radius: 15px !important;
            background-color: #262730 !important;
            color: #FFD700 !important;
            border: 2px solid #464855 !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 보호자 전용 앱 자체 잠금(비밀번호 인증) 로직 ---
def check_password():
    """올바른 비밀번호를 입력한 경우에만 True를 반환합니다."""
    def password_entered():
        # 1. Streamlit Secrets에서 비밀번호 확인, 2. 로컬 환경변수 확인, 3. 없으면 기본값 '7763' 사용
        try:
            expected_pw = str(st.secrets["APP_PASSWORD"])
        except (FileNotFoundError, KeyError):
            expected_pw = os.getenv("APP_PASSWORD", "7763")
            
        if st.session_state["session_password"] == expected_pw:
            st.session_state["password_correct"] = True
            # 보안을 위해 사용자가 입력한 비번 임시 캐시를 메모리에서 즉시 파기
            del st.session_state["session_password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    # 비밀번호 입력창 UI 출력 (블랙&골드 테마 유지)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #FFD700;'>🔒 보호자 전용 로그인 🔒</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FFFFFF; font-size: 18px;'>무단 접속(API 요금 소진)을 통제하기 위해 설정된 비밀번호를 입력해주세요.<br><span style='font-size: 14px; color: #aaaaaa;'>(별도 설정 전 기본 비밀번호는 <b>7763</b> 입니다)</span></p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input(
            "패스워드를 입력하시고 Enter 키를 누르세요", 
            type="password", 
            on_change=password_entered, 
            key="session_password"
        )
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ 비밀번호가 틀렸습니다. 다시 시도하십시오.")
    return False

# 비밀번호가 틀리면 아래에 있는 모든 코드를 절대로 실행하지 않고 즉시 차단
if not check_password():
    st.stop()

st.title("🛡️ MyKidMediaGuard")
st.subheader("기독교 가치관 기반 유튜브 맞춤형 통합 검열기")

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정 (Settings)")
    # 1. Streamlit Cloud의 시크릿 저장소(st.secrets) 최우선 확인
    api_key = None
    try:
        # 배포 시 반드시 필요한 안전한 참조 로직
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("☁️ 서버(st.secrets)에서 API 키를 완벽히 보호하며 연동했습니다.")
    except:
        # 2. 로컬 개발 환경용 폴백 (.env)
        env_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if env_key:
            api_key = env_key
            st.success("✅ 로컬(.env)에서 API 키를 불러왔습니다.")
        else:
            api_key = st.text_input("Google API Key 입력", type="password", help="발급받은 구글 Gemini API 키를 입력하세요.")
    st.markdown("---")
    st.markdown("""
    **💡 앱 소개 및 고도화 기능**
    
    기독교 가치관을 바탕으로 자녀가 시청하려는 유튜브 영상을 완벽히 검증합니다.
    - **오디오 직접 듣기**: 자막 유무와 상관없이 AI가 영상을 직접 듣고 조롱, 비명음, 비속어를 잡아냅니다.
    - **통합 분석**: 영상 제목, 상세 설명, 프레임, 오디오 트랙 전체를 판단에 활용합니다.
    - **연령별 맞춤**: 나이(특히 8~9세 등)에 따라 무서운 소리나 기괴함 판별을 더 엄격히 합니다.
    """)

# --- 주요 화면 구성 ---
youtube_url = st.text_input("🔗 유튜브 URL 입력칸", placeholder="https://www.youtube.com/watch?v=...")
age_options = ["5~7세", "8~9세", "10~11세", "12~13세", "14~15세", "16세 이상"]
selected_age = st.selectbox("👶 연령 선택 드롭다운", age_options)

# --- 기능 함수 정의 ---
def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            # 1. 수동 생성된 한국어/영어 자막 시도
            transcript = transcript_list.find_transcript(['ko', 'ko-KR', 'en'])
        except:
            # 2. 없으면 자동 생성된 한국어 자막까지 샅샅이 검색 (기능 강화)
            try:
                transcript = transcript_list.find_generated_transcript(['ko', 'ko-KR'])
            except:
                # 3. 그래도 없으면 0번째 아무 자막이나 강제 추출
                transcript = next(iter(transcript_list))
        # 자막과 타임스탬프를 함께 결합하여 반환
        text_lines = []
        for t in transcript.fetch():
            start_min = int(t['start'] // 60)
            start_sec = int(t['start'] % 60)
            text_lines.append(f"[{start_min:02d}:{start_sec:02d}] {t['text']}")
        text = "\n".join(text_lines)
        return text
    except Exception as e:
        return ""

def extract_media(url):
    """제목, 설명, 오디오 파일, 비디오 프레임을 모두 추출하는 통합 함수 (403 에러 우회 적용)"""
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, 'audio.m4a')
    video_path = os.path.join(temp_dir, 'video.mp4')
    
    # yt-dlp 옵션: 403 Forbidden 방지를 위해 클라이언트 속이기
    common_args = {'youtube': {'player_client': ['ios', 'tv', 'web']}}
    
    title, description = "제목 없음", "설명 없음"
    # 메타데이터를 다운로드 에러 전에 1차적으로 강제 추출 시도
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                title = info.get('title', '제목 없음')
                description = info.get('description', '')
    except:
        pass

    # 1. 듀얼 엔진 오디오 다운로드 (100% 무료 우회 아키텍처)
    audio_success = False
    err_msg = None
    
    # [새로운 최상위 우회 엔진: 타사 우회 API 연동]
    import requests
    rapidapi_key = None
    try:
        rapidapi_key = st.secrets.get("RAPIDAPI_KEY")
    except:
        rapidapi_key = os.getenv("RAPIDAPI_KEY")
        
    if rapidapi_key:
        try:
            # RapidAPI (Youtube-mp36) 호출로 서버 IP 차단(가짜 DRM) 전면 우회
            vid_id = extract_video_id(url)
            headers = {
                "x-rapidapi-key": rapidapi_key,
                "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
            }
            res = requests.get("https://youtube-mp36.p.rapidapi.com/dl", headers=headers, params={"id": vid_id}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                # 딕셔너리에서 다양한 다운로드 URL 키 시도
                download_url = data.get("link") or data.get("url") or data.get("download") or data.get("mp3")
                
                if download_url:
                    dl_res = requests.get(download_url, timeout=60)
                    with open(audio_path, 'wb') as f:
                        f.write(dl_res.content)
                    audio_success = True
                else:
                    err_msg = f"RapidAPI 응답을 해석할 수 없습니다: {data}"
            else:
                err_msg = f"RapidAPI 접속 거부 (상태코드 {res.status_code}): {res.text}"
        except Exception as api_err:
            err_msg = f"RapidAPI 연결 중 치명적 오류: {api_err}"
    
    # [엔진 1] pytubefix 시도 (API 키가 없거나 실패했을 때 작동하는 백업)
    if not audio_success:
        try:
            from pytubefix import YouTube
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
            if yt.title: title = yt.title
            stream = yt.streams.get_audio_only()
            if stream:
                stream.download(output_path=temp_dir, filename='audio.m4a')
                audio_success = True
        except Exception as e1:
            pass
        
    # [엔진 2] yt-dlp 시도 (최후의 로컬 스크래핑 폴백)
    if not audio_success:
        opts_audio = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': audio_path,
            'extractor_args': common_args,
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(opts_audio) as ydl:
                ydl.download([url])
                audio_success = True
        except Exception as e2:
            if not err_msg:
                err_msg = f"미디어 다운로드 완전 차단됨 (가짜 DRM 차단: {e2})"
            
    if not audio_success:
        return title, description, None, [], temp_dir, err_msg
        
    # 2. 비디오 프레임 추출을 위한 저화질 영상 다운로드
    opts_video = {
        'format': 'worstvideo[ext=mp4]/worst[ext=mp4]/best',
        'outtmpl': video_path,
        'extractor_args': common_args,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts_video) as ydl:
            ydl.download([url])
    except Exception:
        # 비디오 다운로드 실패 시 오디오만으로도 분석 가능하도록 패스
        pass

    # 3. OpenCV 프레임 추출
    frames = []
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames > 0:
                step = max(total_frames // 6, 1)
                for i in range(6):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
                    ret, frame = cap.read()
                    if ret:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        frames.append(img)
            cap.release()

    return title, description, audio_path, frames, temp_dir, None

# --- 실행 버튼 (모바일 환경을 고려해 폭 100% 사용) ---
if st.button("🚀 검열 시작", type="primary", use_container_width=True):
    if not api_key:
        st.warning("👈 좌측 패널에서 Gemini API Key를 먼저 입력해주세요.")
    elif not youtube_url:
        st.warning("유튜브 URL을 입력해주세요.")
    else:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("유효하지 않은 유튜브 URL 형식입니다.")
        else:
            result_text = None
            temp_dir = None
            uploaded_file = None
            
            with st.status("🔍 영상을 분석하고 있습니다 (약 1분 소요)...", expanded=True) as status:
                try:
                    st.write("1. 자막 정보를 확인하는 중...")
                    transcript_text = get_transcript(video_id)
                    if not transcript_text:
                        st.write("⚠️ 자막이 없으므로 오디오와 메타데이터 중심으로 분석합니다.")
                    else:
                        st.write("✅ 자막 텍스트 확보 완료")
                    
                    st.write("2. 영상/오디오 미디어를 안전하게 내려받는 중... (403 우회 모드)")
                    title, desc, audio_path, frames, temp_dir, err = extract_media(youtube_url)
                    
                    if err:
                        st.warning(f"⚠️ 영상 다운로드 서버 차단(403) 발생. 미디어 스캔이 제한되며 '자막 대본' 분석으로 대체합니다. ({err})")
                        audio_path = None
                        frames = []
                    else:
                        st.write(f"✅ 미디어 추출 완료! (제목: {title})")
                    
                    # 치명적 데이터 고갈 방어 로직 (영상/음성 없고 자막도 없는 초유의 사태)
                    blind_mode = False
                    if not transcript_text and not audio_path:
                        blind_mode = True
                        st.error("🚨 전면 데이터 차단! (유튜브 403)")
                        st.warning("유튜브 서버가 자막 추출과 오디오 다운로드를 완벽히 가로막았습니다. AI가 영상의 고유 내용을 **전혀 들을 수 없으므로 오로지 유튜버가 적은 '제목과 설명글' 만으로 평가(Blind Test)**합니다. 결과가 매우 부정확할 수 있습니다!")

                    if frames:
                        st.write("📸 캡처된 프레임 이미지들:")
                        st.image(frames, width=100)
                    
                    st.write("3. 최신 AI 비전 및 오디오 통합 분석 진행 중...")
                    
                    # 새로운 genai.Client 생성 및 파일 업로드
                    client = genai.Client(api_key=api_key)
                    if not err and audio_path and os.path.exists(audio_path):
                        uploaded_file = client.files.upload(file=audio_path)
                        st.write("🎧 오디오 트랙을 AI에게 전송했습니다.")
                    else:
                        st.write("⚠️ 오디오 트랙 없이 자막 데이터 텍스트만으로 정밀 분석을 실시합니다.")
                    
                    prompt = f"""
당신은 기독교 가치관을 지키는 세상에서 가장 엄격하고 정밀한 앱 'MyKidMediaGuard'의 핵심 AI 엔진입니다.
판정 프로세스는 반드시 다음 두 단계로 철저히 분리하여 수행하십시오.

{"🚨 [블라인드 긴급 모드 발동] 현재 이 영상은 유튜브 정책에 의해 오디오 파일과 영상 대본(자막)이 완전히 삭제되어 '제목'과 '설명글' 텍스트밖에는 남지 않았습니다! 절대로 본편 내용이 무해하다고 착각하지 마시고, 요약문 3번 줄에 '본편 데이터 검열불가(제목으로만 제한적 판별)'라는 경고를 반드시 삽입하십시오! 분석 가능한 정보가 부족하다면 rating을 '안전'으로 주지 말고 단어 하나라도 의심되면 즉시 '주의' 혹은 '차단'으로 판단하십시오!" if blind_mode else ""}

[단계 1: 전수 조사 (객관적 사실 탐지 - Detection First)]
사용자가 선택한 타겟 연령대와 무관하게, 영상 내에 존재하는 모든 비속어, 은어, 욕설, 조롱, 시각/청각적 유해 요소를 1초 단위로 완전히 전수 조사하십시오.
- 판단을 섞지 않습니다. "이 정도면 괜찮을 것 같다"는 은폐를 절대 허용하지 않습니다.
- 배경음을 뚫고 들리는 빠른 랩(Rap)이나 웅얼거리는 말투를 단어 단위로 철저히 색출해야 합니다.
- 찾아낸 모든 이슈 사항들을 예외 없이 [timeline_warnings] 배열에 정확한 초 단위 타임코드와 함께 적발하십시오. (AI가 완벽히 알아듣지 못한 웅얼거림 역시 '미확인 위험 요소'로 리스트에 추가하십시오.)

[단계 2: 연령별 적합성 판정 (Age-Based Evaluation)]
위에서 객관적으로 색출된 [단계 1]의 전수 조사 결과를 바탕으로, 사용자가 선택한 연령대의 정서를 기준으로 엄격한 판단을 내려 등급을 매기십시오.
- [검열 대상 연령]: {selected_age}
- [기독교 가치관 엄격도 반영]: 해당 연령의 정서적 한계를 기준으로, 주술적 요소, 보복(복수)의 폭력성, 신성모독 뉘앙스 등 성경적 가치관에 조금이라도 반하는 분위기가 감지될 경우 가차 없이 점수를 깎고 '주의/차단' 등급을 배정하십시오.
- [경고 단어 시각화 지시]: 요약문(analysis_columns) 및 타임라인 작성 시, 적발된 모든 문제 단어 및 비속어(예: '개자식', '돌았나' 등)는 반드시 양쪽에 `<mark>단어</mark>` 형태의 HTML 태그를 씌워 노란색 형광펜 하이라이트 처리가 되도록 강력하게 시각화하십시오.

반드시 응답은 어떠한 리스트 대괄호([])로도 감싸지 말고, 오직 아래의 JSON '단일 객체'({{ ... }}) 형식만 100% 정확히 출력해야 합니다:
{{
  "rating": "안전", // "안전", "주의", "차단" 중 하나만 적을 것
  "scores": {{
    "language_cleanliness": 1, // 1~5점 정수 (5점이 욕설/은어 없음)
    "visual_safety": 1, // 1~5점 정수 (5점이 기괴/폭력성 없음)
    "christian_values": 1 // 1~5점 정수 (5점이 성경적/건전 요소 완벽히 부합)
  }},
  "summary_3_lines": [
    "핵심 이유 1문장 요약",
    "상세 이유 1문장 요약",
    "전수조사 증거에 기반한 최종 결론 1문장"
  ],
  "analysis_columns": {{
    "audio_language": "Phase 1에서 발견된 언어/청각 탐지 내용 상세",
    "visual": "Phase 1에서 발견된 시각 폭력/기괴 탐지 내용 상세",
    "christian_value": "Phase 1에서 발견된 기독교 세계관 반영 여부 탐지 상세"
  }},
  "timeline_warnings": [
    {{"time": "01:23", "issue": "비속어 '개빡침' 감지"}},
    {{"time": "03:45", "issue": "미확인 위험 요소: 불길한 브금 및 판독 불가 발언"}}
  ]
}}

[메타 데이터]
---
제목: {title}
설명: {(desc or "")[:1000]}
자막: {(transcript_text or "")[:5000]}
"""
                    content_parts = []
                    if uploaded_file:
                        content_parts.append(uploaded_file)
                    content_parts.append(prompt)
                    if frames:
                        content_parts.extend(frames)
                    
                    st.write(f"⏳ 최신 모델(gemini-3-flash-preview) 추론 시작...")
                    
                    model_id = "gemini-3-flash-preview"
                    generate_content_config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2, # 엄격하고 일관된 판정을 위해 온도 낮춤
                    )
                    
                    # 🧠 [가변 해상도 두뇌 자동 변속 로직]
                    # 자막이 아예 없어서 구글의 '귀(청각)' 능력을 극한으로 끌어올려야 하는 경우 최고급 Pro 모델 발동!
                    smart_model = 'gemini-1.5-flash'
                    if blind_mode:
                        smart_model = 'gemini-1.5-flash'
                    elif not transcript_text and audio_path:
                        smart_model = 'gemini-1.5-pro-latest'
                        st.info("🧠 자막 데이터가 존재하지 않아, 최고성능 청취 엔진(Gemini 1.5 Pro)으로 자동 터보 변속합니다!")
                    
                    st.write(f"⏳ 채택된 모델({smart_model}) 추론 시작...")
                    
                    # 로딩 방패 애니메이션 및 감성 메시지
                    loading_bar = st.progress(30, text=f"🛡️ 가디언 엔진({smart_model})이 미디어의 가치관을 정밀 스캔 중입니다...")
                    
                    status.update(label="🛡️ 가디언 엔진이 미디어의 가치관을 정밀 스캔 중입니다...", state="running")
                    
                    response = client.models.generate_content(
                        model=smart_model,
                        contents=content_parts,
                        config=generate_content_config,
                    )
                    
                    loading_bar.progress(100, text="✅ 모든 정밀 분석이 완료되었습니다!")
                        
                    result_text = response.text
                    status.update(label="✅ 최고 수준의 다층 분석 완료!", state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"Gemini API 데이터 전송 또는 분석 중 오류가 발생했습니다: {e}")
                    status.update(label="❌ 분석 실패", state="error")
                
                finally:
                    # 클린업
                    if uploaded_file:
                        try:
                            # 신규 클라이언트 API에 맞춘 삭제 명령어
                            client.files.delete(name=uploaded_file.name)
                        except:
                            pass
                    if temp_dir:
                        try:
                            shutil.rmtree(temp_dir)
                        except:
                            pass
                            
            # --- st.status 바깥 (결과 화면) ---
            if result_text:
                import json
                st.markdown("<br>", unsafe_allow_html=True)
                
                # AI가 보낸 ```json 백틱 및 불순물 세척
                clean_result = result_text.strip()
                if clean_result.startswith("```"):
                    lines = clean_result.split("\n")
                    if len(lines) >= 2:
                        clean_result = "\n".join(lines[1:-1]).strip()
                
                try:
                    parsed = json.loads(clean_result)
                    if isinstance(parsed, list):
                        data = parsed[0] if len(parsed) > 0 else {}
                    elif isinstance(parsed, dict):
                        data = parsed
                    else:
                        data = {}
                except json.JSONDecodeError:
                    data = {}
                    st.error("JSON 포맷 해석에 실패했습니다. AI가 반환한 원본 내용을 표시합니다.")
                    st.markdown(result_text)
                    
                def clean_html(text):
                    """ AI가 임의로 집어넣은 마크다운 코드 블록이나 백틱 기호를 소독하여 태그 렌더링 충돌을 막습니다. """
                    if not isinstance(text, str): return str(text)
                    # 백틱 및 마크다운 오작동 방지 (두줄바꿈 이상의 빈 줄은 HTML 블록을 깨뜨리므로 <br>로 강제 변환)
                    cleaned = text.replace("```html", "").replace("```json", "").replace("```", "").replace("`", "").strip()
                    cleaned = cleaned.replace("\n", "<br>")
                    return cleaned

                if data:
                    rating = clean_html(data.get("rating", "알 수 없음"))
                    scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
                    analysis = data.get("analysis_columns") if isinstance(data.get("analysis_columns"), dict) else {}
                    
                    st.subheader("💡 AI 통합 리포트")
                    st.markdown("---")
                    
                    if "안전" in rating:
                        st.markdown('<div class="safe" style="color: white !important;">✅ 최종 종합 판정: 안전<br><span style="font-size: 18px; font-weight: normal; color: white !important;">영상에 유해한 요소가 전혀 감지되지 않아 편안하게 시청 가능합니다.</span></div>', unsafe_allow_html=True)
                    elif "차단" in rating:
                        st.markdown('<div class="block" style="color: white !important;">🚫 최종 종합 판정: 차단<br><span style="font-size: 18px; font-weight: normal; color: white !important;">기독교 가치관에 깊이 위배되거나 정서적 위험 요소가 다수 감지되었습니다.</span></div>', unsafe_allow_html=True)
                    elif "주의" in rating:
                        st.markdown('<div class="warning" style="color: white !important;">⚠️ 최종 종합 판정: 주의<br><span style="font-size: 18px; font-weight: normal; color: white !important;">일부 우려되는 요소가 발견되었습니다. 부모님의 지도가 필요합니다.</span></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="warning" style="color: white !important;">📍 **최종 종합 판정: {rating}**</div>', unsafe_allow_html=True)
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.markdown("### 📝 AI의 결론 3줄 요약")
                    for sentence in data.get("summary_3_lines", []):
                        st.markdown(f"- **{clean_html(sentence)}**", unsafe_allow_html=True)
                        
                    st.markdown("<br><hr>", unsafe_allow_html=True)
                    
                    timeline = data.get("timeline_warnings", [])
                    if timeline:
                        st.markdown("### 📊 [객관적 탐지 리포트] Phase 1: 무관용 전수조사 스캔 리스트")
                        for warn in timeline:
                            time_str = clean_html(warn.get('time', '알 수 없음'))
                            issue_str = clean_html(warn.get('issue', ''))
                            # st.error 대신 커스텀 div를 써서 <mark> 태그 강제로 렌더링되게 처리
                            warn_html = f"""<div style="background-color: rgba(255, 75, 75, 0.15); border-left: 4px solid #ff4b4b; padding: 12px 18px; margin-bottom: 10px; border-radius: 6px; color: white !important; font-size: 16.5px;">📍 <strong>{time_str}</strong> : {issue_str}</div>"""
                            st.markdown(warn_html, unsafe_allow_html=True)
                        st.markdown("<br><hr>", unsafe_allow_html=True)
                    
                    # 4. 부문별 상세 리포트 (하이브리드 프리미엄 대시보드)
                    st.markdown("### 🎯 부문별 상세 인포그래픽 리포트")
                    
                    def render_premium_card(score_val, desc, title, fa_icon, accent_color):
                        try:
                            s = int(score_val)
                        except:
                            s = 5
                        
                        if s >= 4:
                            status_text = "✅ 쾌적/안전"
                            border_color = "#39FF14" # 라이트 네온 그린
                            glow = "0 0 12px rgba(57,255,20,0.8)"
                        elif s == 3:
                            status_text = "⚠️ 주의 환기"
                            border_color = "#FF8C00" # 불타는 네온 오렌지
                            glow = "0 0 12px rgba(255,140,0,0.8)"
                        else:
                            status_text = "🚨 즉각 차단"
                            border_color = "#FF073A" # 강렬한 네온 레드
                            glow = "0 0 12px rgba(255,7,58,0.8)"
                            
                        width_pct = (s / 5.0) * 100
                        
                        safe_desc = clean_html(desc)
                        # 통합 3D 프리미엄 HTML 카드 디자인 (Streamlit 마크다운 HTML Block-breaking 버그 방지를 위해 한 줄도 끊기지 않게 연결)
                        card_html = f"""<div class="custom-card" style="border-top: 6px solid {accent_color};"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h3 style="margin: 0; color: {accent_color};"><span style="font-size: 34px; margin-right: 12px; filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.5));">{fa_icon}</span>{title}</h3><span style="font-size: 32px; font-weight: 900; color: #FFFFFF;">{s} <span style="font-size: 18px; font-weight: 600; color: #888888;">/ 5</span></span></div><div style="width: 100%; background-color: #0E1117; border-radius: 10px; height: 14px; margin-bottom: 10px; border: 1px solid #464855;"><div style="width: {width_pct}%; background-color: {border_color}; box-shadow: {glow}; height: 14px; border-radius: 8px; transition: width 1s ease-in-out;"></div></div><div style="text-align: right; font-size: 16px; color: {border_color}; font-weight: 900; margin-bottom: 24px; text-shadow: {glow};">{status_text}</div><div style="font-size: 18px; font-weight: 500; line-height: 1.8; color: white !important;">{safe_desc}</div></div>"""
                        st.markdown(card_html, unsafe_allow_html=True)

                    col_lang, col_vis, col_val = st.columns(3)
                    
                    with col_lang:
                        render_premium_card(scores.get('language_cleanliness', 5), analysis.get('audio_language', '내용 없음'), "언어 및 청각", "🔊", "#D4AF37")
                        
                    with col_vis:
                        render_premium_card(scores.get('visual_safety', 5), analysis.get('visual', '내용 없음'), "시각 및 폭력성", "👁️", "#D4AF37")
                        
                    with col_val:
                        render_premium_card(scores.get('christian_values', 5), analysis.get('christian_value', '내용 없음'), "가치관 및 세계관", "🕊️", "#2A5C82")
                            
                st.components.v1.html("<script>window.parent.scrollTo(0, document.body.scrollHeight);</script>", height=0)

