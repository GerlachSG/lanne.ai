"""
Inference Service - Servico de inferencia LLM com quantizacao 8-bit
Porta: 8002
Responsabilidades:
- Carregar e gerenciar modelo Qwen2.5-7B-Instruct com quantizacao
- Endpoint /internal/classify para classificacao de intencao
- Endpoint /internal/generate para geracao de texto
- Otimizacao de VRAM com BitsAndBytes

MUDANCAS v2:
- Modelo: Qwen2.5-7B-Instruct (mais estavel que Mistral)
- Quantizacao: 8-bit (melhor qualidade, cabe em 12GB)
- Adicionado: repetition_penalty para evitar loops
- Adicionado: pos-processamento para limpar resposta
"""

from fastapi import FastAPI, HTTPException, status
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)
import torch
from typing import Optional
import logging
import time
import re

from lanne_schemas import LLMRequest, LLMResponse

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Inference Service",
    description="Servico de inferencia LLM com Qwen2.5-7B-Instruct",
    version="2.0.0"
)

# =============================================================================
# CONFIGURACAO DO MODELO
# =============================================================================

# Modelo principal - Qwen2.5 e muito mais estavel que Mistral
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

# Alternativas caso queira testar outros:
# MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # Tambem muito bom
# MODEL_NAME = "microsoft/Phi-3-medium-4k-instruct"  # Menor, mais rapido

FALLBACK_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"  # Fallback menor

# Usar 8-bit ao inves de 4-bit (melhor qualidade, ainda cabe em 12GB)
USE_8BIT = True


class LLMService:
    """
    Servico de gerenciamento do LLM
    Implementa quantizacao 8-bit para balanco qualidade/VRAM
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.model_name = None
        
    def load_model(self):
        """
        Carrega o modelo com quantizacao 8-bit
        """
        try:
            logger.info(f"Carregando modelo: {MODEL_NAME}")
            
            # Detectar dispositivo disponivel
            if torch.cuda.is_available():
                self.device = "cuda"
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"CUDA disponivel. GPU: {torch.cuda.get_device_name(0)}")
                logger.info(f"VRAM disponivel: {vram_gb:.2f} GB")
                
                # Escolher quantizacao baseado na VRAM
                if USE_8BIT and vram_gb >= 10:
                    # 8-bit - melhor qualidade
                    logger.info("Usando quantizacao 8-bit (melhor qualidade)")
                    bnb_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0,
                    )
                else:
                    # 4-bit - economia de VRAM
                    logger.info("Usando quantizacao 4-bit NF4")
                    bnb_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True
                    )
                
                # Carregar modelo com quantizacao
                self.model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch.bfloat16,
                )
                self.model_name = MODEL_NAME
                
            else:
                logger.warning("CUDA nao disponivel. Usando CPU com modelo menor")
                self.device = "cpu"
                
                # Fallback para modelo menor em CPU
                self.model = AutoModelForCausalLM.from_pretrained(
                    FALLBACK_MODEL,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                )
                self.model_name = FALLBACK_MODEL
            
            # Carregar tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Configurar pad_token se nao existir
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info(f"Modelo carregado: {self.model_name} em {self.device}")
            
            # Log de memoria usada
            if self.device == "cuda":
                mem_used = torch.cuda.memory_allocated() / 1e9
                logger.info(f"VRAM usada pelo modelo: {mem_used:.2f} GB")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            raise
    
    def _clean_response(self, text: str) -> str:
        """
        Limpa a resposta gerada:
        - Remove emojis
        - Remove repeticoes
        - Remove tokens especiais residuais
        """
        # Remover emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        
        # Remover tokens especiais do Qwen
        text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', text, flags=re.DOTALL)
        text = re.sub(r'<\|im_start\|>', '', text)
        text = re.sub(r'<\|im_end\|>', '', text)
        text = re.sub(r'<\|endoftext\|>', '', text)
        
        # Remover repeticoes de linhas
        lines = text.split('\n')
        seen = set()
        unique_lines = []
        for line in lines:
            line_normalized = re.sub(r'\d+', 'N', line.strip())
            if line_normalized not in seen or len(line_normalized) < 20:
                seen.add(line_normalized)
                unique_lines.append(line)
        text = '\n'.join(unique_lines)
        
        # Remover sequencias numericas repetidas (1, 10, 100, 1000...)
        text = re.sub(r'(\d+[\s,]+){4,}', '', text)
        
        # Limpar espacos extras
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.15
    ) -> LLMResponse:
        """
        Gera texto usando o LLM com controle de repeticao
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Modelo nao carregado")
        
        try:
            start_time = time.time()
            
            # Tokenizar entrada
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=4096  # Qwen suporta contexto maior
            )
            
            # Mover para o dispositivo correto
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Gerar com parametros otimizados
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=max(temperature, 0.01),  # Evitar divisao por zero
                    top_p=top_p,
                    top_k=40,
                    do_sample=True,
                    repetition_penalty=repetition_penalty,  # Evita loops
                    no_repeat_ngram_size=4,  # Evita repetir sequencias de 4 tokens
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decodificar apenas os novos tokens
            input_length = inputs["input_ids"].shape[1]
            generated_tokens = outputs[0][input_length:]
            generated_text = self.tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True
            )
            
            # Limpar resposta
            generated_text = self._clean_response(generated_text)
            
            inference_time = (time.time() - start_time) * 1000  # ms
            
            logger.info(f"Gerados {len(generated_tokens)} tokens em {inference_time:.2f}ms")
            
            return LLMResponse(
                generated_text=generated_text,
                tokens_generated=len(generated_tokens),
                inference_time_ms=inference_time
            )
            
        except Exception as e:
            logger.error(f"Erro durante geracao: {e}")
            raise


# Instancia global do servico
llm_service = LLMService()


@app.on_event("startup")
async def startup_event():
    """
    Carregar modelo na inicializacao do servico
    """
    logger.info("Iniciando Inference Service...")
    try:
        llm_service.load_model()
        logger.info("Inference Service pronto")
    except Exception as e:
        logger.error(f"Falha ao iniciar servico: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "inference-service",
        "status": "running",
        "model": llm_service.model_name,
        "device": llm_service.device,
        "version": "2.0.0"
    }


@app.post("/internal/classify", response_model=LLMResponse)
async def classify(request: LLMRequest):
    """
    Endpoint de classificacao de intencao
    Usa temperatura baixa para respostas deterministicas
    """
    try:
        logger.info("Requisicao de classificacao recebida")
        
        # Sobrescrever temperatura para classificacao
        response = llm_service.generate(
            prompt=request.prompt,
            max_tokens=min(request.max_tokens, 50),
            temperature=0.1,
            top_p=request.top_p,
            repetition_penalty=1.0  # Sem penalidade para classificacao
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erro na classificacao: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/internal/generate", response_model=LLMResponse)
async def generate(request: LLMRequest):
    """
    Endpoint de geracao de texto
    Usa parametros otimizados para evitar loops
    """
    try:
        logger.info("Requisicao de geracao recebida")
        
        response = llm_service.generate(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            repetition_penalty=1.15  # Penalidade para evitar loops
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erro na geracao: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/info")
async def model_info():
    """Informacoes detalhadas do modelo"""
    info = {
        "model_name": llm_service.model_name,
        "device": llm_service.device,
        "quantization": "8-bit" if USE_8BIT else "4-bit NF4",
    }
    
    if llm_service.device == "cuda":
        info["vram_used_gb"] = round(torch.cuda.memory_allocated() / 1e9, 2)
        info["vram_total_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
    
    return info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)