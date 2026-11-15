# Changelog

## Unreleased

### Học từ câu trả lời

- `query` giờ dùng bộ nhớ làm việc chứ không chỉ hiển thị nó:
  - Node mà `reflect` đã xác nhận là nguồn tốt (preferred, tentative) được xếp
    trước trong số node khớp câu hỏi. Bài học có file đã đổi thì không được tính.
  - Câu hỏi có phần lớn từ giống một câu đã lưu là `useful` sẽ xuất phát từ các
    node câu đó đã chỉ ra, và kết quả ghi rõ đã nhớ lại từ câu nào.
  - Câu hỏi sau đó bị lưu lại là `dead_end` thì không còn được nhớ lại.
- Lệnh `query` qua CLI giờ cũng ghi `learning=…` trên các dòng NODE, như qua MCP.
- Luật always-on (CLAUDE.md, AGENTS.md, GEMINI.md) nhắc agent chạy
  `pilothify save-result … --outcome useful|dead_end` khi kết quả giúp được hoặc
  dẫn sai. Số token của luật vẫn đúng bằng mức cũ.
- `python -m tools.adherence <repo>` đọc transcript Claude Code và đếm số lần
  agent hỏi graph so với grep/đọc file, kèm số token. Trên monorepo thử nghiệm,
  57 phiên trước khi cài pilothify đã dùng 4.134 lần grep/glob/đọc file, trả về
  khoảng 2,8 triệu token.

### Tài liệu

- README ghi đúng biến bật query log (`PILOTHIFY_QUERY_LOG_ENABLE=1`). Log mặc
  định tắt.
- Skill ghi chi phí thật của pass semantic, khoảng 25 nghìn token mỗi file,
  thay vì "vài chục nghìn token" cho cả lượt.
- Tác giả plugin và marketplace là ThangND4, khớp với chủ bản quyền.

## v0.1.2 — 2026-11-15

History của repo bắt đầu lại từ bản này. Tag `v0.1.0` và `v0.1.1` không còn,
nên cài từ `v0.1.2` trở đi. Hai mục bên dưới vẫn được giữ làm ghi chú.

### License

- Chủ bản quyền là ThangND4, ghi trong NOTICE, README và metadata của gói.
  README nói rõ được dùng thương mại và nêu các điều kiện của Apache-2.0.
- Phần nhắc dự án gốc chỉ còn mức license bắt buộc: khối NOTICE gốc và
  LICENSE-MIT. Link tới repo của họ đã được bỏ.

### Sửa lỗi

- **C++: `definition_file` lệch với `source_file`.** Khi gộp khai báo trong
  header với định nghĩa trong `.cpp`, `definition_file` được ghi bằng khóa nội
  bộ, tính tương đối từ root đã resolve. Với file nằm ngoài root, hoặc root đi
  qua symlink như `/var` → `/private/var` trên macOS, nó giữ nguyên chuỗi `../`
  dài trong khi `source_file` đã được rút về tên gọn. Nay nó lấy chính
  `source_file` của định nghĩa, nên được chuẩn hóa giống hệt.

### CI

- Thêm job chạy toàn bộ test trên macOS.
- Test kiểm skill không bị thay lệnh trong backtick giờ đọc vết của bash từ
  stderr. Trước đây nó dùng `BASH_XTRACEFD`, biến chỉ có từ bash 4.1, nên trên
  bash 3.2 của macOS file vết luôn rỗng và test qua mà không kiểm gì.

## v0.1.1 — 2026-11-15

### Sửa lỗi

- **T-SQL bị đọc sai khi cài theo README.** `uv tool install` và `pip` không đọc
  `uv.lock` mà lấy bản mới nhất `pyproject.toml` cho phép. Extra `sql` không giới
  hạn phiên bản, nên kéo `tree-sitter-sql` 0.3.13 thay vì bản 0.3.11 đã test.
  Bản 0.3.13 làm mất thủ tục `[dbo].[x]`, ghi `DELETE`/`UPDATE`/`SELECT INTO`
  sai chiều đọc/ghi và để bảng tạm lọt vào graph. Nay grammar được ghim
  `==0.3.11` ở các extra `sql`, `postgres` và `all`.

### CI

- Thêm job chạy toàn bộ test trên bản cài **không theo lock** (Python 3.13 và
  3.14), giống cách người dùng cài. CI chạy thêm mỗi thứ Hai, để một bản phát
  hành mới của dependency làm hỏng cài đặt sẽ lộ ra kể cả khi không có commit.

### Tài liệu

- README ghi lệnh cài plugin đã kiểm được
  (`claude plugin install pilothify --marketplace thangnd96/pilothify`, hoặc hai
  bước `/plugin marketplace add` rồi `/plugin install` trong Claude Code), và nói
  rõ chỉ chọn một cách đăng ký skill: plugin hoặc `pilothify install`.
- README ghi chi phí thật của pass semantic (khoảng 4,8 triệu token cho 203 tài
  liệu) và khuyên chạy `--code-only` trước trên repo nhiều docs.

## v0.1.0 — 2026-11-14

Bản phát hành đầu tiên. pilothify dựa trên một dự án mã nguồn mở theo
Apache-2.0; nguồn gốc và phần ghi công nằm trong [NOTICE](NOTICE). Bản này đã
chạy trọn trên một monorepo thật: Java Spring, React/TypeScript, game Phaser
và khoảng 200 tài liệu tiếng Việt, tổng cộng 41.807 node.

### Cài đặt chỉ từ repo này

- Tên `pilothify` trên PyPI không phải của dự án. Skill trước đây tự chạy
  `uv tool install pilothify`, `pip install pilothify`, và để dò interpreter thì
  chạy `uv tool run --from pilothify`. Lệnh cuối tải từ PyPI **ở mỗi lần chạy**
  nếu pilothify chưa được cài bằng `uv tool`, kể cả khi đã cài trong venv. Ai
  đăng ký cái tên đó sẽ chạy được code trên máy của bất kỳ ai dùng skill.
- Nay skill dò bằng `uv tool dir` và cài từ
  `git+https://github.com/thangnd96/pilothify`. Mọi gợi ý cài extra trong thông
  báo lỗi cũng trỏ về đó.
- Có thêm plugin Claude Code (`.claude-plugin/`):
  `/plugin install pilothify --marketplace thangnd96/pilothify`.

### Docs nối với code

- **Cùng một mã ở nhiều file** (`BUG-ADM-15-01` trong ca test và trong báo cáo
  QE, `D-20`, `GR-06`, `ADR-0008`): mỗi file vẫn giữ node riêng, được nối với
  nhau bằng `same_key_as`. `explain "BUG-ADM-15-01"` trả node chính thay vì báo
  nhập nhằng.
- **Route của handler Spring** được lưu ở `attributes.route`, ví dụ
  `PUT /api/v1/game/cinema/screen`; `explain` in nó ra. Nhờ đó thấy ngay một
  lệnh `@AdminCommand` nằm ngoài `/ctrl`, điều trước đây chỉ phát hiện được bằng
  cách đọc code.
- **Docs nhắc tới endpoint** nối về handler bằng `references_route`.
- Trên monorepo thử nghiệm: 602 cạnh `same_key_as`, 166 cạnh `references_route`,
  153 trên 155 mapping Spring có route.

### Chi phí

Mọi text gửi cho agent (skill, reference, luật always-on, thông điệp hook,
system prompt trích xuất) đều bằng hoặc dưới bản gốc, đo theo từng file.

- **Ảnh, âm thanh, video trong thư mục asset của app** không đi vào pass
  semantic: trên monorepo thử nghiệm là 2.815 file, tức khoảng 2.800 lượt gọi LLM.
  Pass semantic còn 12 lượt cho 203 tài liệu. `PILOTHIFY_ASSET_MEDIA=1` đưa chúng
  vào lại.
- **Kiểm độ phủ** đếm dòng như `wc -l`. Trước đây một file đọc đủ nhưng không có
  xuống dòng cuối bị coi là đọc thiếu, và lần `--update` sau phải trả thêm một
  subagent (khoảng 460k token) để đọc lại nó.

### Sửa lỗi

- Class và constructor cùng tên trong một file: tra cứu chọn đúng theo nhãn.
- `import type` không còn tạo vòng import giả khi gặp re-export.
- Câu hỏi tiếng Việt không còn khớp nhầm vào mảnh chữ đã bỏ dấu.
- God node không còn bị file test và file config chiếm chỗ.

### Biết trước

- Route mới có cho Java Spring. Express, FastAPI, NestJS chưa có.
- Các test `watch` không ổn định khi chạy song song bằng pytest-xdist, nên CI
  chạy tuần tự.
