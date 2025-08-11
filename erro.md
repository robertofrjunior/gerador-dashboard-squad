Traceback (most recent call last):
  File "/home/nava/relatorios/gerador-dashboard-squad/metricas/metricas/lib/python3.12/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 571, in _run_script
    code = self._script_cache.get_bytecode(script_path)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/nava/relatorios/gerador-dashboard-squad/metricas/metricas/lib/python3.12/site-packages/streamlit/runtime/scriptrunner/script_cache.py", line 72, in get_bytecode
    filebody = magic.add_magic(filebody, script_path)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/nava/relatorios/gerador-dashboard-squad/metricas/metricas/lib/python3.12/site-packages/streamlit/runtime/scriptrunner/magic.py", line 45, in add_magic
    tree = ast.parse(code, script_path, "exec")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/ast.py", line 52, in parse
    return compile(source, filename, mode, flags,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/nava/relatorios/gerador-dashboard-squad/metricas/interface_web.py", line 273
    st.rerun()
IndentationError: unexpected indent
2025-08-08 17:12:30.242 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
