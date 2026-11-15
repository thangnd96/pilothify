# Changelog

## Unreleased

### Cần Python 3.11 trở lên

- Bỏ hỗ trợ Python 3.10 (đã hết hạn hỗ trợ từ 10/2026). Lý do: cờ `-P` của
  Python, dùng để chặn import từ thư mục hiện tại (xem mục sửa lỗi bên dưới),
  chỉ có từ 3.11. Ai đang dùng 3.10 hãy cài lại bằng
  `uv tool install --upgrade "pilothify @ git+https://github.com/thangnd96/pilothify"`;
  uv sẽ tự chọn Python phù hợp.

### `query` trúng hơn nhiều

- Node docstring giờ giữ tới 400 ký tự của docstring để tìm kiếm. Trước đây chỉ
  có nhãn 80 ký tự, nên khoảng 2/3 số docstring bị cắt và phần còn lại không
  bao giờ được dùng để khớp. Phần lưu thêm qua cùng bước che thông tin đăng
  nhập như nhãn, và không được in ra trong kết quả.
- Khớp trong docstring được cộng điểm nhiều hơn (trọng số 0,75 lên 3,0), vì câu
  hỏi viết bằng lời thường thường khớp phần văn xuôi chứ không khớp tên định
  danh. Khớp đúng nhãn vẫn đứng trên rất xa.
- Đo bằng `tools/query_eval` với 123 câu hỏi; 46 câu được để riêng, không dùng
  khi chỉnh. Trên 46 câu để riêng:
  - Đáp án là điểm xuất phát: 13 → 36.
  - Đáp án nằm trong 5 kết quả đầu: 13 → 36.
  - Đáp án có mặt trong kết quả: 23 → 41.
  - MRR: 0,208 → 0,727.
- Cache AST lên schema 46.

### Dọn dẹp

- Không còn comment hay docstring nào mang số issue. Các câu có số issue chen
  giữa đã được viết lại, cùng vài mẩu câu bị gãy từ đợt dọn trước. Các ghi chú
  nhắc phiên bản cũ (0.9.x, 0.7.0) nay ghi là "older releases".

### Sửa lỗi

- **Thư mục `pilothify/` trong repo đang phân tích có thể bị chạy thay cho gói
  đã cài.** `update`, `extract`, `cluster-only` và `label` tự chạy lại chính nó
  bằng `python -m pilothify` để cố định `PYTHONHASHSEED`. Cả `-m` lẫn `-c` đều
  đặt thư mục hiện tại lên đầu `sys.path`, nên nếu repo có thư mục `pilothify/`,
  tiến trình mới và mọi process con của pool sẽ import thư mục đó, tức là chạy
  code của repo. Hook git (probe chọn interpreter, phần dựng lại graph) và
  merge driver cũng chạy ở gốc repo và gặp đúng lỗi này. Nay các chỗ đó bỏ thư
  mục hiện tại khỏi `sys.path` trước khi import gì khác, và dùng thêm `-P`.
  Hook cũng chỉ nhận đường dẫn tuyệt đối từ `pilothify-out/.pilothify_python`,
  để repo không thể trỏ nó tới một file của chính repo.
- **Skill cũng chạy Python ngay trong repo đang phân tích.** Mọi khối
  `$(cat pilothify-out/.pilothify_python) -c "..."` / `-m ...`, bước dò
  interpreter ở Step 1 (trước đây chạy `import pilothify` trong thư mục repo),
  lệnh `pip install` và bản Windows nay đều chạy với `-P`. Như vậy một thư mục
  `pilothify/`, `networkx/` hay `pip/` trong repo không thể chen vào thay gói
  thật. Số token của mọi file skill vẫn không vượt mức trần, nhờ rút gọn vài
  câu lặp ý.
- **Process con của pool ghi cache vào thư mục khác với process cha.** Tên thư
  mục cache AST gồm phiên bản pilothify, mà mỗi process con theo kiểu spawn
  lại tự đọc phiên bản đó từ metadata. Khi một `*.egg-info` trong mã nguồn bị
  build lại giữa chừng (nó đứng trước site-packages trong `sys.path`), process
  con đọc phiên bản mới, còn process cha giữ phiên bản cũ. Process con ghi cache
  vào chỗ process cha không đọc, rồi bước dọn thư mục cũ của process cha xóa
  luôn chỗ đó. Nay process con dùng đúng không gian tên cache của process cha.
  Đây là gốc của 6 test terraform chỉ hỏng khi chạy song song ở máy, và chỉ ở
  lần chạy đầu sau khi nâng phiên bản.
- **Lời gọi client bị nhận nhầm thành route.** `import type { Request } from
  'express'` (hay gặp trong service NestJS) từng đủ để mở phần nhận diện
  Express, và `axios.post('/x', payload)` thành một node route. Nay chỉ tính
  import thật, và chỉ tính lời gọi trên biến tạo từ `express()`, `Router()`,
  `fastify()`, `new Hono()`… hoặc tên `app`, `router`, `server`, `fastify`.
- **Route bị thiếu:**
  - Chuỗi đăng ký kiểu Koa và Hono `router.get('/', h).post('/users', h)` chỉ
    giữ route đầu tiên; nay giữ đủ.
  - Handler bọc trong `asyncHandler(fn)` bị bỏ; nay được nhận và nối tới `fn`.
  - Comment xen giữa `@Get(...)` và method NestJS làm mất route.
  - Flask `methods=["GET", "POST"]` chỉ giữ method đầu; nay giữ đủ.
- **Route Flask không nối được với doc.** Tham số `<int:user_id>` nay được ghi
  thành `{user_id}`, giống cách doc và các framework khác viết.
- **Nối nhầm route theo method.** `route_links` không biết `HEAD`, `OPTIONS`,
  `ALL`, nên doc ghi `DELETE /api/items` từng nối vào handler `HEAD`. Nay các
  method này được nhận, và `ALL` khớp mọi method. Khi khớp chiều route ngắn hơn
  doc, path trong URL của host khác không còn được xét, và phần đuôi dài nhất
  có method khớp mới được chọn.
- **`query` sập trên graph có cạnh song song** (MultiDiGraph) khi một docstring
  khớp câu hỏi.
- **Lưu `dead_end` với cách viết khác không hủy được câu `useful` cũ.** Câu trả
  lời đã lưu giờ được so theo bộ từ khóa, không theo nguyên văn câu hỏi.
- **`tools/adherence.py` đếm sai:** lệnh `$(cat …) -m pilothify update` từng bị
  tính là grep, grep ở dòng thứ hai của lệnh nhiều dòng bị bỏ sót, và
  `grep -rn "pilothify query"` bị tính là hỏi graph. Nay mỗi lệnh con được xét
  theo chương trình nó chạy.
- **Test build wheel không còn ghi vào mã nguồn.** Hai test này build từ một bản
  sao các file đã track, nên `pilothify.egg-info` và `build/` trong repo không
  bị ghi lại giữa lần chạy test.

## v0.1.4 — 2026-11-15

### Route ngoài Spring

- **NestJS:** `@Get(':id')`… được ghép với `@Controller('users')` và ghi lên
  method.
- **FastAPI và Flask:** `@router.get("/x")`, `@bp.route("/x", methods=[…])` được
  ghép với `prefix=` của `APIRouter` hoặc `url_prefix=` của `Blueprint` khai
  báo trong cùng file.
- **Express, Koa router, Fastify, Hono:** `router.get('/x', handler)` và
  `router.route('/x').get(…)` thành node route, nối tới handler khi handler là
  hàm trong cùng file. Chỉ áp dụng cho file có import một trong các thư viện
  đó, nên `axios.get('/x', data)` không bị nhận nhầm.
- **Doc ghi đủ path vẫn nối được:** khi route ngắn hơn path trong doc vì thiếu
  prefix gắn ở file khác (`include_router`, `app.use`), `references_route` vẫn
  khớp theo phần đuôi dài nhất, miễn là duy nhất và có ít nhất 2 đoạn.
- Cache AST lên schema 45, nên file Python và JS/TS trong cache được trích xuất
  lại.

### `query` trúng hơn

- Khi một docstring khớp câu hỏi, chính hàm, class hay file nó mô tả được dùng
  làm điểm xuất phát, với điểm của docstring.
- Đo bằng `python -m tools.query_eval` (30 câu hỏi về mã nguồn pilothify):
  - Đáp án là điểm xuất phát: 9 → 11 câu.
  - Đáp án nằm trong 5 kết quả đầu: 9 → 11 câu.
  - Đáp án có mặt trong kết quả: 23 → 24 câu.
  - MRR: 0,211 → 0,248.

### Sửa lỗi

- **Process pool bị tắt oan.**
  - Gọi từ `python -c`, REPL hoặc test runner thì `__main__` không có file. Khi
    đó extract vẫn dùng được pool, vì spawn bỏ qua `__main__`; chỉ một
    `__file__` không tồn tại (như stdin) mới làm pool hỏng.
  - Trên macOS, lần extract đầu và các lần sau từng cho kết quả khác nhau, vì
    "chưa chọn start method" bị hiểu là "không phải spawn".
- **Test watch chập chờn khi chạy song song.** Bộ test vá `time.sleep` cho toàn
  process. Khi rebuild chờ `git rev-parse` qua `subprocess`, vòng chờ của
  `subprocess` gọi nhầm hàm giả đó và dừng watch giữa chừng. Giờ test chỉ thay
  đồng hồ của module watch.

### Dọn dẹp

- Bỏ khoảng 3.600 số issue cũ (`(#1234)`) khỏi comment, docstring và thông báo.
  Những chỗ số issue chen giữa câu thì giữ nguyên.
- Đổi tên 9 file test có số issue trong tên.

## v0.1.3 — 2026-11-15

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

### Windows

- CI chạy toàn bộ test trên Windows. Lần chạy đầu lộ ra 17 lỗi:
  - Bộ skill của plugin luôn bị coi là cũ, vì danh sách file dùng dấu `\`.
  - Khai báo và định nghĩa C++ nằm ở ổ đĩa khác root không được gộp.
  - Các test chạy shell gọi nhầm trình khởi chạy WSL thay vì bash của Git.
  - Một test watch kỳ vọng dấu `\`, trong khi graph lưu đường dẫn dạng `/`.

  Cả 17 lỗi đã được sửa.

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
