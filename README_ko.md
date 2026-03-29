# AION2 HUD 에디터 & Dat 디코더 ⚙️

[🇺🇸 English](README.md) | [🇯🇵 日本語](README_ja.md) | [🇨🇳 简体中文](README_zh.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Unreal Engine](https://img.shields.io/badge/Unreal_Engine-5-black)

AION2의 `DeviceSetting.dat` 파일을 디코딩하여 미리 보고 편집할 수 있는 독립형 리버싱 툴입니다. 
클라이언트의 로컬 HUD 제한을 우회하여 여러 캐릭터 간에 HUD 레이아웃과 채팅 탭 설정을 자유롭게 복사, 백업 및 수정할 수 있습니다. 클라이언트 패치로 인해 파싱되지 않는 헤더 데이터가 발생할 경우를 대비하여 가상 ID(Virtual ID)를 할당하는 페일세이프(Fail-safe) 메커니즘이 포함되어 있습니다.

*(여기에 10초짜리 시연 GIF 삽입: .dat 열기 -> 캐릭터 선택 -> 레이아웃 복사 -> 저장)*

## 📥 빠른 다운로드
소스 코드를 직접 컴파일하기 번거롭다면 미리 빌드된 독립형 실행 파일을 즉시 다운로드하십시오:
👉 **[AION2_HUD_Editor_V2.exe 다운로드 (v2.0)](https://github.com/victoriousian/AION2_HUD_Editor_V2/releases/tag/v2.0)**

## ⚠️ 주의사항
이 프로젝트는 커뮤니티 주도로 개발된 비공식 리버싱 툴입니다. 클라이언트 파일(`.dat`)을 변조하는 행위에 대한 책임은 사용자 본인에게 있습니다. 항상 원본 설정을 별도로 백업해 두십시오. 툴을 통해 저장할 때마다 자동으로 `.bak` 백업 파일이 생성됩니다.

## 🚀 주요 기능
* **XOR & UTF-16LE/UTF-8 디코딩:** AION2 로컬 세이브 데이터의 하이브리드 컨테이너 구조를 완벽하게 언패킹합니다.
* **가상 ID 복구 (Virtual ID Recovery):** 클라이언트 패치로 인해 바이너리 헤더 오프셋이 어긋날 경우, 식별 불가 블록에 `0xFF0000XX` 대역의 가상 ID를 부여하여 데이터가 소실되는 현상(Silent Drop)을 원천 차단합니다.
* **직관적인 HUD 미리보기:** 확장 가능한 캔버스 위에 미니맵, 채팅창, 퀵슬롯 등 UI 요소의 정확한 앵커와 오프셋 좌표를 렌더링합니다.
* **레이아웃 클로닝:** 단 한 번의 클릭으로 본캐의 HUD 배치와 채팅 탭 설정을 부캐들에게 덮어씌울 수 있습니다.
* **JSON 내보내기/불러오기:** 개별 캐릭터의 원본 JSON 페이로드를 추출하여 다른 유저와 레이아웃 세팅을 공유할 수 있습니다.

## 🛠️ 소스코드 직접 빌드
실행 파일을 직접 빌드하고자 하는 경우 다음 절차를 따르십시오:

1. 레포지토리 클론:
   ```bash
   git clone https://github.com/victoriousian/AION2_HUD_Editor_V2.git
   cd AION2_HUD_Editor_V2
   ```
2. PyInstaller 설치:
   ```bash
   pip install pyinstaller
   ```
3. 빌드 스크립트 실행 (Windows):
   ```bash
   build.bat
   ```
   *컴파일된 실행 파일은 `dist/` 폴더에 생성됩니다.*

## 📖 사용 방법
1. `AION2_HUD_Editor.exe`를 실행합니다.
2. 찾아보기를 눌러 본인의 `DeviceSetting.dat` 파일을 선택합니다.
    * *기본 경로: `C:\Users\{사용자명}\AppData\Local\AION2\Saved\PersistentDownloadDir\UserSetting\DeviceSetting.dat`*
3. **열기 (디코딩 시작)** 버튼을 클릭합니다. 툴이 바이너리 헤더와 JSON 페이로드를 파싱합니다.
4. 패치로 인해 본캐의 헤더 오프셋이 변경되었다면, 가상 ID(예: `0xFF000000`)로 안전하게 로드됩니다. 드롭다운에서 해당 ID를 선택하십시오.
5. **레이아웃 복사** 버튼을 사용하여 설정값을 다른 캐릭터에게 클론합니다.
6. **DAT 저장** 버튼을 클릭합니다. 덮어쓰기 전 자동으로 타임스탬프가 포함된 `.bak` 파일이 생성됩니다.

## 🤝 후원 및 지원
수많은 부캐들의 UI를 세팅해야 하는 노가다를 이 툴이 덜어주었다면, 향후 클라이언트 패치에 대응하기 위한 지속적인 리버싱 및 유지보수 작업에 후원을 고려해 주십시오.

🎁 **BTC 지갑 주소:** `1JADombahDcTHR4yNywfWKtckt7zKyNHwF`

## 📝 라이선스
MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하십시오.
