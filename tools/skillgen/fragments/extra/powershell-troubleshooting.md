## Troubleshooting

### PowerShell 5.1: Vertical scrolling stops working

If vertical scrolling breaks in PowerShell after running pilothify, this is caused by ANSI escape sequences from the `graspologic` library. pilothify suppresses this output; if you still see it:

1. **Upgrade pilothify**: `pip install --upgrade 'pilothify @ git+https://github.com/thangnd96/pilothify'`
2. **Use Windows Terminal** instead of the legacy PowerShell console, which mishandles ANSI codes
3. **Reset your terminal**: close and reopen PowerShell
4. **Skip Leiden**: uninstall its backend (`pip uninstall graspologic` on Python < 3.13, `pip uninstall graspologic-native` on Python 3.13+) and pilothify will fall back to NetworkX's built-in Louvain algorithm, which produces no ANSI output

---
