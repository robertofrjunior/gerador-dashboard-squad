"""
Sistema de processamento em lote para múltiplas sprints.
"""

import pandas as pd
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple, Callable
import time
from dataclasses import dataclass
from ..utils.log import info, warn, error
from ..sprint_service import analisar_sprint


@dataclass
class SprintTask:
    """Representa uma tarefa de processamento de sprint."""
    projeto: str
    sprint_id: int
    priority: int = 1  # 1 = alta, 2 = média, 3 = baixa


@dataclass
class BatchResult:
    """Resultado do processamento em lote."""
    successful_sprints: List[Tuple[int, pd.DataFrame]]
    failed_sprints: List[Tuple[int, str]]
    processing_time: float
    total_items: int


class SprintBatchProcessor:
    """Processador em lote para múltiplas sprints."""
    
    def __init__(self, max_workers: int = 3, timeout: int = 30):
        """
        Inicializa o processador.
        
        Args:
            max_workers: Número máximo de workers paralelos
            timeout: Timeout para cada operação em segundos
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.results_cache: Dict[str, BatchResult] = {}
    
    def process_sprints_parallel(
        self, 
        tasks: List[SprintTask],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult:
        """
        Processa sprints em paralelo usando ThreadPoolExecutor.
        
        Args:
            tasks: Lista de tarefas para processar
            progress_callback: Callback para reportar progresso
            
        Returns:
            Resultado do processamento em lote
        """
        start_time = time.time()
        successful_sprints = []
        failed_sprints = []
        
        # Ordenar por prioridade
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)
        
        info(f"Iniciando processamento em lote de {len(tasks)} sprints")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as tarefas
            future_to_task = {
                executor.submit(self._process_single_sprint, task): task
                for task in sorted_tasks
            }
            
            completed_count = 0
            total_tasks = len(tasks)
            
            # Processar resultados conforme completam
            for future in as_completed(future_to_task, timeout=self.timeout * len(tasks)):
                task = future_to_task[future]
                completed_count += 1
                
                try:
                    df = future.result(timeout=self.timeout)
                    if df is not None and not df.empty:
                        successful_sprints.append((task.sprint_id, df))
                        info(f"✅ Sprint {task.sprint_id} processada ({len(df)} itens)")
                    else:
                        failed_sprints.append((task.sprint_id, "Sem dados retornados"))
                        warn(f"⚠️ Sprint {task.sprint_id} sem dados")
                        
                except Exception as e:
                    failed_sprints.append((task.sprint_id, str(e)))
                    error(f"❌ Sprint {task.sprint_id} falhou: {e}")
                
                # Reportar progresso
                if progress_callback:
                    progress_callback(completed_count, total_tasks)
        
        # Calcular métricas finais
        processing_time = time.time() - start_time
        total_items = sum(len(df) for _, df in successful_sprints)
        
        result = BatchResult(
            successful_sprints=successful_sprints,
            failed_sprints=failed_sprints,
            processing_time=processing_time,
            total_items=total_items
        )
        
        info(f"Processamento concluído: {len(successful_sprints)} sucessos, "
             f"{len(failed_sprints)} falhas em {processing_time:.1f}s")
        
        return result
    
    def _process_single_sprint(self, task: SprintTask) -> Optional[pd.DataFrame]:
        """
        Processa uma única sprint.
        
        Args:
            task: Tarefa da sprint
            
        Returns:
            DataFrame com dados da sprint ou None se falhar
        """
        try:
            df = analisar_sprint(task.projeto, task.sprint_id)
            
            if df is not None and not df.empty:
                # Adicionar metadados
                df['Sprint ID'] = task.sprint_id
                df['Sprint Nome'] = df.attrs.get('sprint_nome', f'Sprint {task.sprint_id}')
                return df
            
        except Exception as e:
            error(f"Erro ao processar sprint {task.sprint_id}: {e}")
            
        return None
    
    def combine_sprint_data(self, batch_result: BatchResult) -> pd.DataFrame:
        """
        Combina dados de múltiplas sprints em um DataFrame unificado.
        
        Args:
            batch_result: Resultado do processamento em lote
            
        Returns:
            DataFrame combinado
        """
        if not batch_result.successful_sprints:
            return pd.DataFrame()
        
        # Combinar todos os DataFrames
        dfs_to_combine = []
        sprint_info = []
        
        for sprint_id, df in batch_result.successful_sprints:
            dfs_to_combine.append(df)
            sprint_info.append({
                'id': sprint_id,
                'nome': df.attrs.get('sprint_nome', f'Sprint {sprint_id}'),
                'inicio': df.attrs.get('sprint_inicio'),
                'fim': df.attrs.get('sprint_fim'),
                'total_itens': len(df),
            })
        
        # Combinar DataFrames
        combined_df = pd.concat(dfs_to_combine, ignore_index=True)
        
        # Adicionar metadados ao DataFrame combinado
        combined_df.attrs['sprint_info'] = sprint_info
        combined_df.attrs['processing_time'] = batch_result.processing_time
        combined_df.attrs['failed_sprints'] = batch_result.failed_sprints
        
        return combined_df
    
    def get_batch_summary(self, batch_result: BatchResult) -> Dict[str, Any]:
        """
        Gera resumo do processamento em lote.
        
        Args:
            batch_result: Resultado do processamento
            
        Returns:
            Dicionário com resumo
        """
        success_rate = (
            len(batch_result.successful_sprints) / 
            (len(batch_result.successful_sprints) + len(batch_result.failed_sprints)) * 100
            if (batch_result.successful_sprints or batch_result.failed_sprints) else 0
        )
        
        return {
            'total_sprints_requested': len(batch_result.successful_sprints) + len(batch_result.failed_sprints),
            'successful_sprints': len(batch_result.successful_sprints),
            'failed_sprints': len(batch_result.failed_sprints),
            'success_rate': round(success_rate, 1),
            'total_items': batch_result.total_items,
            'processing_time': round(batch_result.processing_time, 2),
            'items_per_second': round(
                batch_result.total_items / batch_result.processing_time
                if batch_result.processing_time > 0 else 0, 1
            )
        }


class PaginatedProcessor:
    """Processador com paginação para grandes volumes de dados."""
    
    def __init__(self, page_size: int = 50):
        """
        Inicializa processador paginado.
        
        Args:
            page_size: Número de itens por página
        """
        self.page_size = page_size
    
    def process_in_chunks(
        self,
        data_source: Callable[[], List[Any]],
        processor: Callable[[List[Any]], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Processa dados em chunks para evitar sobrecarga de memória.
        
        Args:
            data_source: Função que retorna dados completos
            processor: Função para processar cada chunk
            progress_callback: Callback para progresso
            
        Returns:
            Lista de resultados processados
        """
        all_data = data_source()
        total_items = len(all_data)
        results = []
        
        # Processar em chunks
        for i in range(0, total_items, self.page_size):
            chunk = all_data[i:i + self.page_size]
            result = processor(chunk)
            results.append(result)
            
            if progress_callback:
                progress_callback(min(i + self.page_size, total_items), total_items)
        
        return results


def create_sprint_tasks(projeto: str, sprint_ids: List[int]) -> List[SprintTask]:
    """
    Cria lista de tarefas para processamento em lote.
    
    Args:
        projeto: Nome do projeto
        sprint_ids: Lista de IDs das sprints
        
    Returns:
        Lista de tarefas ordenadas por prioridade
    """
    tasks = []
    
    for i, sprint_id in enumerate(sprint_ids):
        # Sprints mais recentes têm prioridade maior
        priority = 1 if i < 3 else 2 if i < 6 else 3
        
        tasks.append(SprintTask(
            projeto=projeto,
            sprint_id=sprint_id,
            priority=priority
        ))
    
    return tasks