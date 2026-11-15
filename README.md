# pilothify

Biến một codebase (kèm docs, schema SQL, config, PDF, ảnh) thành **knowledge graph** để AI agent hỏi graph thay vì grep và đọc từng file.

- **Code được phân tích tại máy, không gọi LLM.** tree-sitter dựng AST, sau đó một lượt nối lời gọi, import và kế thừa giữa các file. Cùng input luôn ra cùng graph.
- **Mỗi cạnh đều có nhãn tin cậy:** `EXTRACTED` (ghi rõ trong source), `INFERRED` (suy ra theo luật, kèm điểm), `AMBIGUOUS` (cần người xem lại).
- **Không dùng vector store.** Graph thật, truy vấn bằng cách đi theo cạnh.

## Cài đặt

Cần Python 3.10 đến 3.14 và [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/thangnd96/pilothify.git && cd pilothify
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ".[leiden,mcp,sql]"
```

Hoặc cài thành công cụ dùng chung cho mọi project: `uv tool install "pilothify[leiden,mcp,sql] @ git+https://github.com/thangnd96/pilothify"`.

Các extra khác (`pdf`, `office`, `video`, `watch`, `terraform`, `anthropic`, `ollama`, …) xem trong `pyproject.toml`.

Luôn cài từ repo này. Tên `pilothify` trên PyPI không phải của dự án, nên đừng chạy `pip install pilothify` trần. Skill cũng chỉ tự cài từ GitHub.

## Dùng trong Claude Code

Đăng ký skill bằng **một** trong hai cách. Dùng cả hai thì skill bị đăng ký hai lần.

- **Plugin**, không cần cài CLI trước. Lần chạy đầu, skill tự cài CLI từ GitHub nếu máy chưa có.

  ```bash
  claude plugin install pilothify --marketplace thangnd96/pilothify
  ```

  Hoặc ngay trong Claude Code: `/plugin marketplace add thangnd96/pilothify`, rồi `/plugin install pilothify@pilothify-marketplace`. Skill gọi bằng `/pilothify:pilothify`.

- **CLI** đã cài như trên: `pilothify install`. Skill gọi bằng `/pilothify`.

Cách nào cũng vậy, hook và luật trong CLAUDE.md cài bằng CLI:

```bash
pilothify claude install    # thêm luật vào CLAUDE.md và hook nhắc agent hỏi graph trước khi grep
pilothify hook install      # git hook: cập nhật graph sau mỗi commit
```

Sau đó gõ `/pilothify .` trong Claude Code (bản plugin: `/pilothify:pilothify .`). Các assistant khác: `pilothify install --platform <tên>` (codex, cursor, gemini, …).

## Dùng từ dòng lệnh

```bash
PILOTHIFY_BACKEND=none pilothify extract . --code-only   # chỉ code, không cần API key
pilothify cluster-only .                                 # chia community, sinh GRAPH_REPORT.md và graph.html
pilothify update .                                       # cập nhật sau khi sửa code (chỉ AST)

pilothify query "spin wallet debit"                      # subgraph cho một câu hỏi
pilothify explain "SpinService"                          # một node và các kết nối của nó
pilothify path "SpinController" "WalletApi"              # hai thứ nối với nhau thế nào
```

`query`, `path`, `explain` trả mã thoát 0 khi có kết quả, 3 khi tên mơ hồ, 4 khi không khớp. Kết quả ghi vào `pilothify-out/`: `graph.json`, `GRAPH_REPORT.md`, `graph.html` và `cache/`.

Câu hỏi tiếng Việt: từ có dấu chỉ khớp với label tiếng Việt (sinh ra từ pass semantic trên docs). Với graph chỉ có code, hãy hỏi bằng tên định danh trong code.

## Cấu hình

- `.pilothifyignore`: thêm mẫu loại trừ, ngoài `.gitignore`.
- `.pilothifyrc`: `key=value` cho từng dự án, ví dụ `query_budget=4000`, `query_depth=3`, `language.inc=php`.
- Biến môi trường `PILOTHIFY_*`, ví dụ `PILOTHIFY_BACKEND=none` (tắt mọi LLM backend), `PILOTHIFY_OUT` (thư mục output), `PILOTHIFY_HOOK_STRICT=1` (hook chặn hẳn thay vì chỉ nhắc), `PILOTHIFY_QUERY_LOG_ENABLE=1` (ghi các câu hỏi vào `~/.cache/pilothify-queries.log`; mặc định tắt), `PILOTHIFY_ASSET_MEDIA=1` (đưa cả ảnh, âm thanh, video asset vào pass semantic).

## Docs nối với code

- **Cùng một mã ở nhiều file** (`BUG-ADM-15-01`, `D-20`, `GR-06`, `ADR-0008`): mỗi file vẫn giữ node của mình, nhưng được nối với nhau bằng cạnh `same_key_as`. `pilothify explain "BUG-ADM-15-01"` trả về node chính thay vì báo nhập nhằng. Mã phải có dấu `-` và có số (`Q5`, `G2` bị bỏ qua vì hay trùng giữa các tài liệu).
- **Route của handler** được lưu ở `attributes.route`, ví dụ `PUT /api/v1/game/cinema/screen`. `query` tìm được theo route, còn `explain` in nó ra. Path dùng hằng số hay biến thì bỏ qua, để không đoán sai.
  - Spring: `@RequestMapping`, `@GetMapping`… ghép với prefix ở mức class.
  - NestJS: `@Get(':id')`… ghép với `@Controller('users')`.
  - FastAPI và Flask: `@router.get("/x")`, `@bp.route("/x", methods=[…])`, ghép với `prefix=` của `APIRouter` hoặc `url_prefix=` của `Blueprint` khai báo trong cùng file.
  - Express, Koa router, Fastify, Hono: `router.get('/x', handler)`, chuỗi `router.get(…).post(…)` và `router.route('/x').get(…)` thành một node route, nối tới handler nếu handler là hàm khai báo trong cùng file (kể cả khi bọc trong `asyncHandler(fn)`). Chỉ xét file có import thật một trong các thư viện đó (`import type` không tính), và chỉ xét lời gọi trên biến tạo từ `express()`, `Router()`, `fastify()`, `new Hono()`… hoặc tên `app`, `router`, `server`, `fastify`. Nhờ vậy lời gọi client như `axios.post('/x', data)` hay `this.http.get(…)` không bị nhận nhầm.
  - Prefix gắn ở file khác (`include_router`, `app.use('/api', r)`, `setGlobalPrefix`) không biết được, nên route chỉ mang phần của chính nó.
- **Docs nhắc tới endpoint** (`PUT /me/social/shares/{postId}`) nối về handler bằng cạnh `references_route`:
  - Khớp đủ path là EXTRACTED.
  - Khớp phần đuôi theo một trong hai chiều, và chỉ khớp một route, là INFERRED 0,95. Chiều thứ hai là khi route ngắn hơn path trong doc, vì thiếu prefix gắn ở file khác; path nằm trong URL của host khác (`https://api.khac.com/...`) không xét chiều này.
  - Method ghi trong doc phải khớp; route `ALL` (`router.all`, `@All`) khớp mọi method.
  - Mẫu glob như `/ctrl/**` không nối.

## Học từ câu trả lời

- Khi kết quả `query` giúp được (hoặc dẫn sai), agent lưu lại: `pilothify save-result --question "…" --answer "…" --nodes <label> --outcome useful|dead_end`. Luật trong CLAUDE.md nhắc agent làm việc này. File lưu ở `pilothify-out/memory/`.
- `pilothify reflect` gom các file đó thành `pilothify-out/reflections/LESSONS.md` và `.pilothify_learning.json`. Git hook của pilothify chạy lệnh này sau mỗi commit.
- `query` dùng lại hai thứ đó:
  - Trong các node khớp câu hỏi, node đã được xác nhận hữu ích được xếp lên trước. Bài học có file đã đổi từ lúc lưu thì không được tính.
  - Câu hỏi có phần lớn từ giống một câu đã lưu là `useful` sẽ bắt đầu từ các node câu đó đã chỉ ra, và dòng đầu kết quả ghi `Recalled from a saved answer to: …`.
  - Câu hỏi sau đó bị lưu lại là `dead_end` thì không còn được nhớ lại.
- Không tốn token, không cần chạy lại pass semantic. Bài học không bao giờ kéo vào kết quả một node không liên quan tới câu hỏi.

Muốn biết agent có thật sự hỏi graph không, chạy `python -m tools.adherence <repo> --since <ngày cài>` từ thư mục pilothify. Lệnh đọc transcript Claude Code của repo đó và đếm số lần hỏi graph so với số lần grep/đọc file, kèm số token mỗi bên. Chạy thêm không có `--since` để có số liệu nền từ trước khi cài.

## Chi phí

- Phân tích code không tốn token LLM. Chỉ pass semantic trên docs/ảnh mới gọi LLM, và kết quả được cache theo nội dung file.
- **Pass semantic tốn nhiều hơn bạn nghĩ.** Trên một monorepo thật, 203 tài liệu tốn khoảng 4,8 triệu token: 12 subagent, mỗi cái chừng 65–70 nghìn token ngữ cảnh cố định, cộng phần đọc tài liệu. Skill chỉ dừng lại hỏi khi repo có hơn 500 file. Với repo nhiều docs, hãy chạy `PILOTHIFY_BACKEND=none pilothify extract . --code-only` trước (không tốn token), hoặc chạy `/pilothify` trên một thư mục docs nhỏ.
- Ảnh, âm thanh và video trong thư mục asset của app (`assets/`, `public/`, `sprites/`, `fixtures/`…) không bị gửi đi đọc bằng vision hay chuyển thành văn bản; số file bỏ qua được in ra khi chạy. File trong `docs/`, `design/`, `screenshots/`, `diagrams/`… vẫn được đọc.
- `GRAPH_REPORT.md` xếp hạng god node bỏ qua code test và file cấu hình (yaml/json/toml…).

## Phát triển

```bash
.venv/bin/python -m pytest tests/ -q -n 8   # nhanh; test watch có thể chập chờn khi chạy song song
.venv/bin/python -m pytest tests/ -q        # tuần tự, như CI
```

Kiến trúc và cách thêm ngôn ngữ: [ARCHITECTURE.md](ARCHITECTURE.md). File skill trong `pilothify/` được sinh từ `tools/skillgen/fragments/`, nên sửa fragment rồi chạy `python -m tools.skillgen`, `python -m tools.skillgen --bless`, rồi `python -m tools.build_plugin` để chép skill sang bộ plugin.

Phát hành: tăng `version` cùng lúc ở `pyproject.toml`, `.claude-plugin/plugin.json` và `.claude-plugin/marketplace.json` (có test kiểm), ghi vào [CHANGELOG.md](CHANGELOG.md), rồi gắn tag `vX.Y.Z`.

## License

Apache-2.0, Copyright 2026 ThangND4.

- **Được dùng thương mại:** bán, nhúng vào sản phẩm đóng, sửa và phân phối lại, không bắt mở mã nguồn.
- **Điều kiện:** khi phân phối, giữ nguyên [LICENSE](LICENSE), [NOTICE](NOTICE) và [LICENSE-MIT](LICENSE-MIT), và ghi rõ nếu đã sửa file.

pilothify phát triển từ một dự án mã nguồn mở khác. Phần ghi công mà license của dự án đó bắt buộc nằm trong NOTICE và LICENSE-MIT.
