"""
Sistema de criptografia para dados sensíveis.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import streamlit as st
from datetime import datetime, timedelta
import json
from ..utils.log import info, warn, error


class SecurityManager:
    """Gerenciador de segurança para dados sensíveis."""
    
    def __init__(self):
        """Inicializa o gerenciador de segurança."""
        self._session_key = None
        self._fernet = None
        self.session_timeout = timedelta(minutes=30)
    
    def _get_or_create_key(self) -> bytes:
        """
        Obtém ou cria uma chave de criptografia para a sessão.
        
        Returns:
            Chave de criptografia
        """
        if self._session_key is None:
            # Gerar chave única para esta sessão
            session_id = st.session_state.get('session_id', secrets.token_hex(16))
            
            # Usar PBKDF2 para derivar chave da session_id
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'jira-dashboard-salt',  # Salt fixo para consistência na sessão
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(session_id.encode()))
            self._session_key = key
            
        return self._session_key
    
    def _get_fernet(self) -> Fernet:
        """Obtém instância do Fernet para criptografia."""
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def encrypt_token(self, token: str) -> str:
        """
        Criptografa um token de API.
        
        Args:
            token: Token em texto plano
            
        Returns:
            Token criptografado em base64
        """
        try:
            fernet = self._get_fernet()
            encrypted_token = fernet.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_token).decode()
        except Exception as e:
            error(f"Erro ao criptografar token: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Descriptografa um token de API.
        
        Args:
            encrypted_token: Token criptografado em base64
            
        Returns:
            Token em texto plano
        """
        try:
            fernet = self._get_fernet()
            encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_token = fernet.decrypt(encrypted_data)
            return decrypted_token.decode()
        except Exception as e:
            error(f"Erro ao descriptografar token: {e}")
            raise
    
    def store_credentials(self, jira_url: str, email: str, token: str) -> Dict[str, str]:
        """
        Armazena credenciais criptografadas na sessão.
        
        Args:
            jira_url: URL do Jira
            email: Email do usuário
            token: Token de API
            
        Returns:
            Dicionário com credenciais criptografadas
        """
        try:
            encrypted_token = self.encrypt_token(token)
            
            credentials = {
                'jira_url': jira_url,  # URL não é sensível
                'email': email,       # Email não é sensível
                'encrypted_token': encrypted_token,
                'stored_at': datetime.now().isoformat(),
                'session_id': st.session_state.get('session_id')
            }
            
            # Armazenar na sessão
            st.session_state['jira_credentials'] = credentials
            
            info("Credenciais armazenadas com segurança")
            return credentials
            
        except Exception as e:
            error(f"Erro ao armazenar credenciais: {e}")
            raise
    
    def get_credentials(self) -> Optional[Dict[str, str]]:
        """
        Recupera credenciais descriptografadas da sessão.
        
        Returns:
            Dicionário com credenciais ou None se não encontradas/expiradas
        """
        try:
            credentials = st.session_state.get('jira_credentials')
            
            if not credentials:
                return None
            
            # Verificar se a sessão não expirou
            stored_at = datetime.fromisoformat(credentials['stored_at'])
            if datetime.now() - stored_at > self.session_timeout:
                warn("Sessão expirada, limpando credenciais")
                self.clear_credentials()
                return None
            
            # Descriptografar token
            decrypted_token = self.decrypt_token(credentials['encrypted_token'])
            
            return {
                'jira_url': credentials['jira_url'],
                'email': credentials['email'],
                'token': decrypted_token
            }
            
        except Exception as e:
            error(f"Erro ao recuperar credenciais: {e}")
            self.clear_credentials()
            return None
    
    def clear_credentials(self) -> None:
        """Limpa credenciais da sessão."""
        if 'jira_credentials' in st.session_state:
            del st.session_state['jira_credentials']
        info("Credenciais limpas da sessão")
    
    def is_authenticated(self) -> bool:
        """
        Verifica se o usuário está autenticado.
        
        Returns:
            True se autenticado, False caso contrário
        """
        return self.get_credentials() is not None
    
    def hash_sensitive_data(self, data: str) -> str:
        """
        Cria hash de dados sensíveis para logs.
        
        Args:
            data: Dados sensíveis
            
        Returns:
            Hash SHA256 dos dados
        """
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    
    def sanitize_for_log(self, text: str) -> str:
        """
        Sanitiza texto removendo dados sensíveis para logs.
        
        Args:
            text: Texto original
            
        Returns:
            Texto sanitizado
        """
        # Mascarar tokens e emails
        import re
        
        # Mascarar tokens (sequências longas alfanuméricas)
        text = re.sub(r'\b[A-Za-z0-9]{20,}\b', '[TOKEN_MASKED]', text)
        
        # Mascarar emails
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_MASKED]', text)
        
        # Mascarar URLs com credenciais
        text = re.sub(r'https?://[^@]+@[^\s]+', '[URL_WITH_CREDS_MASKED]', text)
        
        return text


class RateLimiter:
    """Rate limiter para controlar chamadas de API."""
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 1):
        """
        Inicializa o rate limiter.
        
        Args:
            max_requests: Máximo de requisições por janela
            window_minutes: Tamanho da janela em minutos
        """
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = []
    
    def can_make_request(self, user_id: str = None) -> bool:
        """
        Verifica se pode fazer uma requisição.
        
        Args:
            user_id: ID do usuário (opcional)
            
        Returns:
            True se pode fazer requisição, False caso contrário
        """
        now = datetime.now()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Usar session_id como user_id se não fornecido
        if user_id is None:
            user_id = st.session_state.get('session_id', 'anonymous')
        
        # Limpar requisições antigas
        self.requests = [
            (timestamp, uid) for timestamp, uid in self.requests
            if timestamp > window_start
        ]
        
        # Contar requisições do usuário na janela atual
        user_requests = [
            timestamp for timestamp, uid in self.requests
            if uid == user_id
        ]
        
        # Verificar se pode fazer nova requisição
        if len(user_requests) < self.max_requests:
            self.requests.append((now, user_id))
            return True
        
        return False
    
    def get_remaining_requests(self, user_id: str = None) -> int:
        """
        Retorna número de requisições restantes.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Número de requisições restantes
        """
        if user_id is None:
            user_id = st.session_state.get('session_id', 'anonymous')
        
        now = datetime.now()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        user_requests = [
            timestamp for timestamp, uid in self.requests
            if uid == user_id and timestamp > window_start
        ]
        
        return max(0, self.max_requests - len(user_requests))


# Instâncias globais
security_manager = SecurityManager()
rate_limiter = RateLimiter(max_requests=100, window_minutes=1)


def require_authentication(func):
    """
    Decorator que requer autenticação.
    
    Args:
        func: Função a ser decorada
        
    Returns:
        Função decorada
    """
    def wrapper(*args, **kwargs):
        if not security_manager.is_authenticated():
            st.error("🔒 Acesso negado. Faça login primeiro.")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper


def rate_limited(func):
    """
    Decorator para rate limiting.
    
    Args:
        func: Função a ser decorada
        
    Returns:
        Função decorada
    """
    def wrapper(*args, **kwargs):
        if not rate_limiter.can_make_request():
            remaining = rate_limiter.get_remaining_requests()
            st.error(f"🚫 Rate limit excedido. Aguarde antes de fazer nova requisição. "
                    f"Requisições restantes: {remaining}")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper