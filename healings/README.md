## Sistema de Healing Automático

### Arquivos necessários para funcionamento:

1. **hp_emergency.png** - Barra de HP com ~10-15% (vermelho escuro)
2. **hp_critical.png** - Barra de HP com ~25-30% (vermelho normal)  
3. **hp_low.png** - Barra de HP com ~45-50% (vermelho claro)
4. **hp_medium.png** - Barra de HP com ~65-70% (mistura vermelho/verde)
5. **hp_high.png** - Barra de HP com ~85-90% (verde claro)
6. **hp_full.png** - Barra de HP com ~100% (verde completo)

### Como capturar as imagens:

1. Execute o script `capture_hp.py` para orientações
2. Use Print Screen para capturar a tela
3. Recorte apenas a barra de HP no Paint
4. Salve com os nomes acima nesta pasta

### Configuração das hotkeys:

Por padrão o sistema usa:
- **F1** - Emergency healing (HP ≤15%)
- **F2** - Critical healing (HP ≤30%)
- **F3** - Low healing (HP ≤50%)
- **F4** - Mana potion

Edite o arquivo `healing.py` para alterar as configurações.