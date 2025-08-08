────────────────────────── Traceback (most recent call last) ───────────────────────────
  /home/nava/relatorios/gerador-dashboard-squad/metricas/metricas/lib/python3.12/site-  
  packages/streamlit/runtime/scriptrunner/exec_code.py:128 in                           
  exec_func_with_error_handling                                                         
                                                                                        
  /home/nava/relatorios/gerador-dashboard-squad/metricas/metricas/lib/python3.12/site-  
  packages/streamlit/runtime/scriptrunner/script_runner.py:669 in code_to_exec          
                                                                                        
  /home/nava/relatorios/gerador-dashboard-squad/metricas/interface_web.py:1458 in       
  <module>                                                                              
                                                                                        
    1455 │   │   │   │   │   │   df_filtrado_sp = df_story_points.copy()                
    1456 │   │   │   else:                                                              
    1457 │   │   │   │   │   │   # Aplicar os mesmos filtros de tipos e SP > 0 (já gar  
  ❱ 1458 │   │   │   │   │   │   mask_tipos_hist = df_hist['Tipo de Item'].apply(lambd  
    1459 │   │   │   │   │   │   df_story_points = df_hist[mask_tipos_hist & (df_hist[  
    1460 │   │   │   │   │   │   # Calcular dias                                        
    1461 │   │   │   │   │   │   df_story_points = calc_dias(df_story_points, 'Data Cr  
────────────────────────────────────────────────────────────────────────────────────────
NameError: name 'df_hist' is not defined
