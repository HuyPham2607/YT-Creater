# CODEX HANDOFF - Tool 8 G-Labs

Ngay 2026-06-09 da tap trung sua Tool 8 G-Labs/Flow automation.

## Da lam duoc

- Viet lai UI Tool 8 theo dang queue/table de nhin ro tung dong prompt.
- Moi dong co cot: Reference, Prompt, Settings, Output, Status.
- Cot Reference hien 5 slot anh co dinh.
- Bam `+` de them anh reference vao slot trong, khong ghi de anh cu nua.
- Moi row luu duoc danh sach nhieu anh reference.
- Engine upload tung anh reference rieng le, khong gop contact sheet nua.
- Anh da upload trong cung batch se duoc cache, prompt sau dung lai thi chi search/add tu library, khong upload lai.
- Da fix luong reference:
  - upload anh len Flow
  - doi anh xuat hien trong asset picker
  - search dung trong bang asset/reference, khong search nham thanh search ngoai
  - click anh
  - bam `Them vao cau lenh`
  - chi submit khi reference attach thanh cong
- Tao extension local `extensions/rx-flow-helper` de ho tro thao tac DOM trong Google Flow.
- Chrome debug/launcher da load extension local bang `--load-extension`.
- Log moi chu yeu da doi sang English de tranh loi mojibake trong terminal.

## Workflow hien tai

1. Nhap prompt vao Tool 8.
2. Chon 1-5 anh reference cho tung row neu can.
3. Tool upload tung anh reference len Flow.
4. Tool go prompt.
5. Tool search va add tung anh reference vao cau lenh.
6. Tool bam tao anh va luu output ve folder da chon.

## Chua lam / can theo doi

- Chua xac minh 100% Flow native co giu duoc nhieu reference thumbnail rieng biet hay khong trong moi model.
- Neu them anh thu 2 van lam anh 1 bien mat tren Flow, can debug tiep nut `+`/attach trong composer cua Flow.
- Extension helper moi la ban noi bo don gian, chua co UI quan ly rieng trong Chrome.
- Chua lam chay song song nhieu luong generation.
- Chua lam phan video/Veo3 chi tiet, hien tap trung vao image flow.
- File `ui/glabs_engine.py` dang co mot so text/comment bi mojibake tu cac lan sua truoc, code van compile duoc nhung nen cleanup encoding sau.

## File chinh da dung

- `ui/tab_glabs.py`
- `ui/glabs_engine.py`
- `launch_chrome.py`
- `extensions/rx-flow-helper/manifest.json`
- `extensions/rx-flow-helper/content.js`
