import re
from typing import Optional, List, Dict

class NameExtractionService:
  def __init__(self):
    self.connectors = ['de', 'del', 'la', 'el', 'los', 'las', 'con', 'y', 'a']
    self.color_words = ["rojo", "azul", "verde", "blanco", "negro", "gris", "amarillo"]
    self.number_words = {
      "un": 1, "una": 1, "uno": 1,
      "dos": 2, "tres": 3, "cuatro": 4,
      "cinco": 5, "seis": 6, "siete": 7,
      "ocho": 8, "nueve": 9, "diez": 10
    }
    self._setup_patterns()
    
  def _setup_patterns(self):        
    self.space_patterns = [
      r"ingresar\s+a\s+espacio\s+(.+)",
      r"entrar\s+al\s+espacio\s+(.+)",
      r"abrir\s+espacio\s+(.+)",
      r"entrar\s+a\s+espacio\s+(.+)",
      r"ir\s+al\s+espacio\s+(.+)",
      r"espacio\s+(.+)",
    ]
    
    self.element_patterns = [
      r"ingresar\s+a\s+elemento\s+(.+)",
      r"entrar\s+al\s+elemento\s+(.+)",
      r"agregar\s+(?:el\s+)?(.+)",
      r"abrir\s+(?:elemento\s+)?(.+)",
      r"registrar\s+(?:el\s+)?(.+)",
      r"elemento\s+(.+)",
      r"item\s+(.+)",
    ]
    
    self.attribute_patterns = {
      'color': [
        r"(?:de\s+)?color\s+(.+)",
        r"es\s+(?:de\s+)?color\s+(.+)",
        r"(?:es|tiene)\s+(negro|blanco|rojo|azul|verde|amarillo|gris|plateado|dorado)",
      ],
      'marca': [
        r"marca\s+(.+)",
        r"de\s+marca\s+(.+)",
        r"es\s+(?:de\s+)?marca\s+(.+)",
      ],
      'modelo': [
        r"modelo\s+(.+)",
        r"es\s+(?:el\s+)?modelo\s+(.+)",
      ],
      'cantidad': [
        r"(?:hay|tiene|son)\s+(\d+)",
        r"cantidad\s+(?:de\s+)?(\d+)",
        r"(\d+)\s+unidades?",
      ],
      'estado': [
        r"estado\s+(.+)",
        r"está\s+(.+)",
        r"condición\s+(.+)",
        r"(?:es|está)\s+(nuevo|usado|dañado|excelente|bueno|regular|malo)",
      ],
      'ubicación': [
        r"ubicado\s+en\s+(.+)",
        r"está\s+en\s+(.+)",
        r"se\s+encuentra\s+en\s+(.+)",
        r"ubicación\s+(.+)",
      ],
      'descripción': [
        r"descripción\s+(.+)",
        r"detalles?\s+(.+)",
        r"es\s+un(?:a)?\s+(.+)",
      ]
    }
    
  def extract_space_name(self, command: str) -> Optional[str]:
    command = command.lower().strip()
        
    for pattern in self.space_patterns:
      match = re.search(pattern, command, re.IGNORECASE)
      if match:
        space_name = match.group(1).strip()
        space_name = self._clean_trailing_words(space_name)
        
        return self._capitalize_name(space_name)
    
    return None
  
  def extract_element_name(self, command: str) -> Optional[str]:
    command = command.lower().strip()
    
    for pattern in self.element_patterns:
      match = re.search(pattern, command, re.IGNORECASE)
      if match:
        element_name = match.group(1).strip()
        element_name = self._clean_trailing_words(element_name)
        
        return self._capitalize_name(element_name)
    
    return None
  
  def extract_elements_from_command(self, command: str) -> List[Dict]:
      command = command.lower().replace("el espacio tiene", "").strip()

      parts = re.split(r",| y ", command)
      elements = []

      for part in parts:
        part = part.strip()
        if not part:
            continue

        amount_match = re.search(r"(\d+|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)", part)
        amount = 1
        if amount_match:
          val = amount_match.group(1)
          amount = int(val) if val.isdigit() else self.number_words.get(val, 1)

        color = None
        for c in self.color_words:
          if c in part:
            color = c
            break

        name_match = re.search(r"(?:\d+|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)?\s*(\w+)", part)
        name = name_match.group(1) if name_match else "elemento"

        elements.append({
          "name": name,
          "amount": amount,
          "color": color
        })

      return elements
  
  def extract_attribute(self, command: str, attribute_type: str) -> Optional[str]:
    command = command.lower().strip()
    if attribute_type not in self.attribute_patterns:
      return None
    
    patterns = self.attribute_patterns[attribute_type]
    for pattern in patterns:
      match = re.search(pattern, command, re.IGNORECASE)
      if match:
        value = match.group(1).strip()
        value = self._clean_trailing_words(value)
        
        if attribute_type == 'cantidad':
            return value
        
        return self._capitalize_name(value)
    
    return None
  
  def _capitalize_name(self, name: str) -> str:
    words = name.split()
    capitalized = []
    
    for i, word in enumerate(words):
      if i == 0:
          capitalized.append(word.capitalize())
      elif word.lower() in self.connectors:
          capitalized.append(word.lower())
      else:
          capitalized.append(word.capitalize())
    
    return ' '.join(capitalized)
    
  
  def _clean_trailing_words(self, text: str) -> str:
    trailing_words = [
      'por favor', 'gracias', 'ahora', 'ya', 
      'también', 'favor', 'porfavor'
    ]
    
    text = text.strip()
        
    for word in trailing_words:
      if text.lower().endswith(word):
        text = text[:-len(word)].strip()
    
    return text
    