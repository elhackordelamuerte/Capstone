import os
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    print("llama_cpp not installed.")

import config

class Summarizer:
    def __init__(self):
        self.model_path = config.LLM_MODEL_PATH
        if not self.model_path.exists():
            print(f"Warning: LLM model not found at {self.model_path}. Please download it.")
            self.llm = None
        else:
            print(f"Loading LLM model: {self.model_path}")
            self.llm = Llama(
                model_path=str(self.model_path), 
                n_ctx=config.N_CTX, 
                n_threads=config.N_THREADS,
                verbose=False # Set to True for debugging
            )
            print("LLM model loaded.")

    def generate_summary(self, transcription_text: str, output_md_path: Path, language: str = 'fr') -> bool:
        if not self.llm:
            print("LLM not initialized properly.")
            return False

        print("Generating summary...")
        
        # System prompt tailored for Qwen2.5/Phi-3.5 instruct formats
        system_prompt = getattr(self, f"_get_prompt_{language}", self._get_prompt_en)()
        
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nVoici la transcription de la réunion :\n\n{transcription_text}<|im_end|>\n<|im_start|>assistant\n"
        
        try:
            output = self.llm(
                prompt,
                max_tokens=2048,
                stop=["<|im_end|>"],
                temperature=0.3,
                top_p=0.9
            )
            
            summary_text = output['choices'][0]['text'].strip()
            
            # Ensure parent directory exists
            output_md_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(summary_text)
                
            print(f"Summary saved to {output_md_path}")
            return True
            
        except Exception as e:
            print(f"Error during summarization: {e}")
            return False

    def _get_prompt_fr(self):
        return """Tu es un assistant expert spécialisé dans la rédaction de comptes-rendus de réunions.
À partir de la transcription fournie, tu dois générer un compte-rendu structuré en Markdown.
Respecte strictement cette structure :
# Compte-rendu de Réunion
## 📋 Résumé exécutif
(Résumé de 3-5 phrases des points essentiels)
## 🗣️ Points abordés
(Liste à puces des différents sujets discutés)
## ✅ Décisions prises
(Liste à puces des décisions validées)
## 🔲 Actions & next steps
(Tableau Markdown avec Responsable, Action, Échéance si mentionnés)
## ❓ Points en suspens
(Liste des questions restées sans réponse)"""

    def _get_prompt_en(self):
        return """You are an expert meeting summarization assistant.
Based on the provided transcript, generate a structured meeting minute in Markdown.
Strictly follow this structure:
# Meeting Minutes
## 📋 Executive Summary
(3-5 sentences summarizing key points)
## 🗣️ Discussion Points
(Bullet points of discussed topics)
## ✅ Decisions Made
(Bullet points of validated decisions)
## 🔲 Action Items
(Markdown table with Assignee, Action, Deadline if mentioned)
## ❓ Open Questions
(List of unanswered questions)"""

    def _get_prompt_es(self):
        return """Eres un asistente experto especializado en la redacción de actas de reuniones.
A partir de la transcripción proporcionada, debes generar un acta estructurada en Markdown.
Respeta estrictamente esta estructura:
# Acta de la Reunión
## 📋 Resumen ejecutivo
(Resumen de 3-5 oraciones de los puntos clave)
## 🗣️ Puntos discutidos
(Lista de viñetas de los diferentes temas tratados)
## ✅ Decisiones tomadas
(Lista de viñetas de las decisiones validadas)
## 🔲 Acciones y próximos pasos
(Tabla Markdown con Responsable, Acción, Fecha límite si se mencionan)
## ❓ Puntos pendientes
(Lista de preguntas sin respuesta)"""

    def _get_prompt_de(self):
         return """Sie sind ein fachkundiger Assistent, der auf das Verfassen von Sitzungsprotokollen spezialisiert ist.
Erstellen Sie anhand der bereitgestellten Transkription ein strukturiertes Protokoll in Markdown.
Beachten Sie unbedingt diese Struktur:
# Besprechungsprotokoll
## 📋 Zusammenfassung
(Zusammenfassung der wichtigsten Punkte in 3-5 Sätzen)
## 🗣️ Besprochene Punkte
(Aufzählung der verschiedenen besprochenen Themen)
## ✅ Getroffene Entscheidungen
(Aufzählung der bestätigten Entscheidungen)
## 🔲 Aktionen & nächste Schritte
(Markdown-Tabelle mit Verantwortlichem, Aktion, Frist, falls erwähnt)
## ❓ Offene Punkte
(Liste der unbeantworteten Fragen)"""

    def _get_prompt_it(self):
         return """Sei un assistente esperto specializzato nella stesura di verbali di riunione.
Dalla trascrizione fornita, devi generare un verbale strutturato in Markdown.
Rispetta rigorosamente questa struttura:
# Verbale della Riunione
## 📋 Sintesi esecutiva
(Riassunto di 3-5 frasi dei punti essenziali)
## 🗣️ Punti discussi
(Elenco puntato dei vari argomenti trattati)
## ✅ Decisioni prese
(Elenco puntato delle decisioni validate)
## 🔲 Azioni e prossimi passi
(Tabella Markdown con Responsabile, Azione, Scadenza se menzionati)
## ❓ Punti in sospeso
(Elenco delle domande rimaste senza risposta)"""
