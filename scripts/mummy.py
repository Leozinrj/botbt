# mummy.py - Automacao de batalha contra múmias e outros inimigos com Arduino HID + Healing
import os, time, pyautogui as pg, serial, ctypes
import cv2, numpy as np
from typing import Optional, Tuple

print("="*50)
print("MUMMY BOT - Automacao com Arduino HID + HEALING")
print("="*50)

COM_PORT = "COM11"  # Porta atualizada conforme disponível
BAUD_RATE = 9600
LOCATE_TIMEOUT = 20.0  # Aumentado para melhor detecção de flags
CONFIDENCE = 0.8  # Aumentado para melhor precisão na detecção

# Configurações de Healing
HEALING_ENABLED = True
HP_CHECK_INTERVAL = 0.5  # Verifica HP a cada 0.5s
HP_REGION = (9, 7, 497, 7)  # Região da barra de HP

# Desativa mouse acceleration no Windows
def disable_mouse_acceleration():
    try:
        ctypes.windll.user32.SystemParametersInfoW(0x0071, 0, 0, 0)
        print("[MOUSE] Aceleracao desativada!")
    except Exception as e:
        print(f"[MOUSE] Erro ao desativar aceleracao: {e}")

disable_mouse_acceleration()

def wait_exact(seconds, msg="Aguardando"):
    print(f"[WAIT] {msg} ({seconds:.1f}s)")
    time.sleep(seconds)

def send_command(ser, cmd):
    try:
        ser.write((cmd + "\n").encode())
        ser.flush()
        return True
    except Exception as e:
        print(f"[SERIAL] Erro: {e}")
        return False

def click_at_position(ser, x, y, right_click=False):
    print(f"[MOUSE] Movendo para ({x},{y})")
    
    max_attempts = 150  # Mais tentativas
    tolerance = 0  # Tolerância zero para máxima precisão
    
    # Primeiro movimento: vai diretamente para próximo da posição
    curr_x, curr_y = pg.position()
    dx = x - curr_x
    dy = y - curr_y
    
    # Se a distância é grande, faz um movimento inicial grande
    if abs(dx) > 300 or abs(dy) > 300:
        large_dx = max(-127, min(127, dx // 2))
        large_dy = max(-127, min(127, dy // 2))
        send_command(ser, f"R {large_dx} {large_dy}")
        time.sleep(0.1)
    
    # Agora faz movimentos precisos
    for attempt in range(max_attempts):
        curr_x, curr_y = pg.position()
        dx = x - curr_x
        dy = y - curr_y
        
        # Verifica se chegou na posição exata
        if dx == 0 and dy == 0:
            print(f"[MOUSE] Posição EXATA alcançada: ({curr_x},{curr_y})")
            break
        
        # Calcula movimento necessário
        if abs(dx) <= 127 and abs(dy) <= 127:
            # Movimento direto se está dentro do limite
            if not send_command(ser, f"R {dx} {dy}"):
                print("[MOUSE] Erro ao mover")
                return False
            time.sleep(0.05)
        else:
            # Movimento em passos
            step_x = max(-127, min(127, dx))
            step_y = max(-127, min(127, dy))
            if not send_command(ser, f"R {step_x} {step_y}"):
                print("[MOUSE] Erro ao mover")
                return False
            time.sleep(0.03)
    
    # Verificação final crítica
    time.sleep(0.15)
    final_x, final_y = pg.position()
    error = abs(x - final_x) + abs(y - final_y)
    print(f"[MOUSE] Final: ({final_x},{final_y}) - Erro: {error}px")
    
    # Se o erro é muito grande, tenta uma correção final
    if error > 5:
        print(f"[MOUSE] Erro alto ({error}px), fazendo correção final...")
        correction_dx = x - final_x
        correction_dy = y - final_y
        if abs(correction_dx) <= 127 and abs(correction_dy) <= 127:
            send_command(ser, f"R {correction_dx} {correction_dy}")
            time.sleep(0.1)
    
    # Pausa crítica antes do clique
    time.sleep(0.3)
    
    # Executa clique
    if right_click:
        result = send_command(ser, "CR")
        print("[MOUSE] Clique direito executado")
    else:
        result = send_command(ser, "C")
        print("[MOUSE] Clique esquerdo executado")
    
    time.sleep(0.3)  # Pausa após clicar
    return result

def press_space(ser):
    print("[TECLADO] Pressionando ESPACO")
    return send_command(ser, "KE SPACE")

def press_p(ser):
    print("[TECLADO] Pressionando P")
    return send_command(ser, "KT p")

def press_backslash(ser):
    print("[TECLADO] Pressionando \\")
    return send_command(ser, "KE \\")

def press_key_3(ser):
    print("[HEALING] Pressionando tecla 3")
    return send_command(ser, "KT 3")

def get_hp_by_color_detection():
    """
    Detecta HP baseado nas cores configuradas das imagens de referência
    hpcheio.png = Verde intenso = HP cheio
    hp80p.png = Verde musgo = HP 80%  
    hpmedio.png = Amarelo = HP médio  
    hpbaixo.png = Vermelho = HP baixo
    """
    try:
        # Captura screenshot da região do HP
        x, y, width, height = HP_REGION
        screenshot = pg.screenshot(region=(x, y, width, height))
        img_array = np.array(screenshot)
        
        total_pixels = 0
        full_hp_pixels = 0      # hpcheio.png - Verde intenso
        hp80_pixels = 0         # hp80p.png - Verde musgo
        medium_hp_pixels = 0    # hpmedio.png - Amarelo/laranja
        low_hp_pixels = 0       # hpbaixo.png - Vermelho
        
        # Analisa cada pixel
        for py in range(height):
            for px in range(width):
                try:
                    b, g, r = img_array[py, px][:3]  # BGR
                    
                    # Pula pixels muito escuros (background)
                    if r < 50 and g < 50 and b < 50:
                        continue
                        
                    total_pixels += 1
                    
                    # hpcheio.png - Verde intenso (HP cheio)
                    if g > 150 and r < 100 and b < 100 and g > r + 30:
                        full_hp_pixels += 1
                    # hp80p.png - Verde musgo (HP 80%)
                    elif g > 120 and r > 80 and r < 140 and b < 80 and g > r:
                        hp80_pixels += 1
                    # hpmedio.png - Amarelo/laranja (DETECÇÃO AMPLIADA)
                    elif (r > 120 and g > 90 and b < 100 and r >= g) or \
                         (r > 100 and g > 80 and b < 80 and r > g - 10) or \
                         (r + g > 180 and b < 100 and abs(r - g) < 60):
                        medium_hp_pixels += 1
                    # hpbaixo.png - Vermelho
                    elif r > 150 and g < 100 and b < 100 and r > g + 50:
                        low_hp_pixels += 1
                        
                except (IndexError, ValueError):
                    continue
        
        if total_pixels == 0:
            return "unknown"
        
        # Calcula percentuais
        full_ratio = full_hp_pixels / total_pixels if total_pixels > 0 else 0
        hp80_ratio = hp80_pixels / total_pixels if total_pixels > 0 else 0
        medium_ratio = medium_hp_pixels / total_pixels if total_pixels > 0 else 0
        low_ratio = low_hp_pixels / total_pixels if total_pixels > 0 else 0
        
        # Debug das cores detectadas
        print(f"[HP DEBUG] Total: {total_pixels}, Cheio: {full_hp_pixels} ({full_ratio:.2%}), 80%: {hp80_pixels} ({hp80_ratio:.2%}), Médio: {medium_hp_pixels} ({medium_ratio:.2%}), Baixo: {low_hp_pixels} ({low_ratio:.2%})")
        
        # Determina estado do HP baseado nas imagens
        if full_ratio > 0.3:  # HP cheio (hpcheio.png)
            return "full"
        elif hp80_ratio > 0.3:  # HP 80% (hp80p.png)
            return "high"
        elif medium_ratio > 0.01 or (total_pixels > 1000 and medium_ratio > 0.005):  # HP médio - MUITO SENSÍVEL
            return "medium"
        elif low_ratio > 0.1:  # HP baixo (hpbaixo.png)
            return "low"
        # Se detectou qualquer pixel que não é verde cheio, considera médio
        elif total_pixels > 500 and full_ratio < 0.8 and hp80_ratio < 0.2:
            return "medium"  # Assume médio se não é verde suficiente
        else:
            return "unknown"
            
    except Exception as e:
        print(f"[HEALING] Erro na detecção de HP: {e}")
        return "unknown"

def check_and_heal(ser):
    """
    Verifica HP e faz healing se necessário
    Apenas HP médio (hpmedio.png) vai usar botão 3
    """
    if not HEALING_ENABLED:
        print("[HEALING] Sistema desabilitado!")
        return False
        
    try:
        hp_state = get_hp_by_color_detection()
        print(f"[HEALING DEBUG] Estado detectado: '{hp_state}'")
        
        if hp_state == "medium":
            # HP médio (hpmedio.png) - aperta 3
            print(f"[HEALING] *** HP MÉDIO DETECTADO! *** Enviando tecla 3...")
            if press_key_3(ser):
                print(f"[HEALING] ✅ Tecla 3 enviada com SUCESSO!")
                # Pequena pausa após healing
                time.sleep(0.5)
                return True
            else:
                print(f"[HEALING] ❌ ERRO ao enviar tecla 3!")
                return False
        elif hp_state == "unknown":
            print(f"[HEALING] HP Estado: {hp_state} - cor desconhecida")
        else:
            print(f"[HEALING] HP Estado: {hp_state} - sem healing necessário")
        
        return False
        
    except Exception as e:
        print(f"[HEALING] ERRO no sistema de healing: {e}")
        return False

def quick_enemy_check(mummy_image, bonebeast_image, scarab_image):
    """
    Verificação RÁPIDA de inimigos - timeout baixo para não atrapalhar outras operações
    Retorna o primeiro inimigo encontrado ou None
    """
    try:
        # Verifica mummy rapidamente
        mummy_pos = pg.locateCenterOnScreen(mummy_image, confidence=0.7)
        if mummy_pos and 10 < mummy_pos.x < pg.size().width - 10 and 10 < mummy_pos.y < pg.size().height - 10:
            return ("mummy", (int(mummy_pos.x), int(mummy_pos.y)))
    except:
        pass
    
    try:
        # Verifica bonebeast rapidamente
        bonebeast_pos = pg.locateCenterOnScreen(bonebeast_image, confidence=0.7)
        if bonebeast_pos and 10 < bonebeast_pos.x < pg.size().width - 10 and 10 < bonebeast_pos.y < pg.size().height - 10:
            return ("bonebeast", (int(bonebeast_pos.x), int(bonebeast_pos.y)))
    except:
        pass
    
    try:
        # Verifica scarab rapidamente
        scarab_pos = pg.locateCenterOnScreen(scarab_image, confidence=0.7)
        if scarab_pos and 10 < scarab_pos.x < pg.size().width - 10 and 10 < scarab_pos.y < pg.size().height - 10:
            return ("scarab", (int(scarab_pos.x), int(scarab_pos.y)))
    except:
        pass
    
    return None

def monitored_wait(ser, seconds, msg, mummy_image, bonebeast_image, scarab_image, current_phase):
    """
    Espera com monitoramento contínuo de inimigos E HEALING
    Se encontrar inimigo durante a espera, para e ataca
    Se HP médio, faz healing
    RETORNA: True se houve interrupção por inimigo, False se completou normalmente
    """
    print(f"[MONITORED WAIT] {msg} ({seconds:.1f}s) - Monitorando inimigos + healing...")
    start_time = time.time()
    end_time = start_time + seconds
    check_interval = 0.5  # Verifica inimigos e HP a cada 0.5s
    
    enemies_found_count = 0
    healings_done = 0
    last_healing_time = 0
    was_interrupted = False
    
    while time.time() < end_time:
        current_time = time.time()
        
        # Verifica healing a cada 0.5s e não muito frequente
        if current_time - last_healing_time > 1.0:  # Pelo menos 1s entre healings
            if check_and_heal(ser):
                healings_done += 1
                last_healing_time = current_time
                print(f"[INTERRUPT] Healing realizado durante {current_phase}! Total: {healings_done}")
        
        # Verifica se há inimigos na tela
        enemy_found = quick_enemy_check(mummy_image, bonebeast_image, scarab_image)
        
        if enemy_found:
            enemy_name, enemy_pos = enemy_found
            enemies_found_count += 1
            remaining_time = end_time - time.time()
            print(f"[INTERRUPT] {enemy_name.upper()} detectado em {enemy_pos} durante {current_phase}!")
            print(f"[INTERRUPT] Pausando espera (restavam {remaining_time:.1f}s) para atacar!")
            
            # Clica no inimigo imediatamente
            print(f"[INTERRUPT] Pressionando \\ antes de atacar {enemy_name}...")
            press_backslash(ser)
            time.sleep(0.2)
            if click_at_position(ser, enemy_pos[0], enemy_pos[1]):
                print(f"[INTERRUPT] {enemy_name.upper()} atacado! Total encontrados: {enemies_found_count}")
                # Delays específicos por inimigo
                if enemy_name == "mummy":
                    delay_time = 5.0
                    print(f"[INTERRUPT] Aguardando {delay_time}s após atacar {enemy_name}...")
                    time.sleep(delay_time)
                elif enemy_name == "bonebeast":
                    delay_time = 8.0
                    print(f"[INTERRUPT] Aguardando {delay_time}s após atacar {enemy_name}...")
                    time.sleep(delay_time)
                elif enemy_name == "scarab":
                    delay_time = 6.0
                    print(f"[INTERRUPT] Aguardando {delay_time}s após atacar {enemy_name}...")
                    time.sleep(delay_time)
                print(f"[INTERRUPT] Retomando {current_phase}...")
                was_interrupted = True  # Marca que houve interrupção
            else:
                print(f"[INTERRUPT] ERRO ao atacar {enemy_name}!")
        
        # Pausa curta antes da próxima verificação
        remaining_time = max(0, end_time - time.time())
        sleep_time = min(check_interval, remaining_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    summary = []
    if enemies_found_count > 0:
        summary.append(f"{enemies_found_count} inimigo(s) atacado(s)")
    if healings_done > 0:
        summary.append(f"{healings_done} healing(s) realizado(s)")
    
    if summary:
        print(f"[MONITORED WAIT] Espera concluída! {', '.join(summary)} durante {current_phase}")
    else:
        print(f"[MONITORED WAIT] Espera concluída! Nenhuma atividade durante {current_phase}")
    
    return was_interrupted  # Retorna se houve interrupção

def locate_image(image_path, timeout=LOCATE_TIMEOUT, confidence=CONFIDENCE):
    filename = os.path.basename(image_path)
    if not os.path.exists(image_path):
        print(f"[ERRO] Imagem nao encontrada: {image_path}")
        return None
    print(f"[BUSCA] {filename} (confidence={confidence:.1f}, timeout={timeout:.1f}s)...")
    deadline = time.time() + timeout
    
    # Para flags, usa método mais preciso
    is_flag = "flag" in filename.lower()
    
    while time.time() < deadline:
        try:
            if is_flag:
                # Para flags: usa método mais rigoroso
                pos = pg.locateCenterOnScreen(image_path, confidence=confidence)
                if pos:
                    # Verifica se a posição é válida (não nos cantos da tela)
                    if 10 < pos.x < pg.size().width - 10 and 10 < pos.y < pg.size().height - 10:
                        print(f"[OK] {filename} encontrado em ({pos.x},{pos.y}) com confidence {confidence}")
                        return (int(pos.x), int(pos.y))
            else:
                # Para inimigos: método normal
                pos = pg.locateCenterOnScreen(image_path, confidence=confidence)
                if pos:
                    print(f"[OK] {filename} encontrado em ({pos.x},{pos.y})")
                    return (int(pos.x), int(pos.y))
        except Exception as e:
            pass
        time.sleep(0.3)  # Pausa um pouco mais para detecção precisa
    
    print(f"[TIMEOUT] {filename} nao encontrado")
    return None

def find_and_click_specific_enemy(ser, mummy_image, bonebeast_image, scarab_image):
    """
    Procura APENAS por mummy, bonebeast e scarab na tela e clica no primeiro encontrado.
    Usa confidence alto para garantir que é realmente o inimigo correto.
    Retorna o nome do inimigo se encontrou e clicou, None caso contrário.
    """
    print("[ENEMY] Procurando APENAS mummy, bonebeast e scarab...")
    
    # Verifica mummy primeiro - confidence alto para precisão - 5 SEGUNDOS
    try:
        mummy_pos = locate_image(mummy_image, timeout=1.5, confidence=0.8)
        if mummy_pos:
            print(f"[ENEMY] MUMMY confirmado em {mummy_pos}! Pressionando \\ antes do ataque...")
            press_backslash(ser)  # PRESSIONA \ ANTES DO ATAQUE
            time.sleep(0.2)
            print(f"[ENEMY] Clicando na MUMMY...")
            if click_at_position(ser, mummy_pos[0], mummy_pos[1]):
                print("[ENEMY] Clique na MUMMY enviado com sucesso!")
                print("[ENEMY] Aguardando 5 segundos após atacar MUMMY...")
                time.sleep(5.0)  # DELAY MUMMY: 5 SEGUNDOS
                print("[ENEMY] Delay de 5s após MUMMY concluído!")
                return "mummy"
    except:
        pass
    
    # Verifica bonebeast - 8 SEGUNDOS
    try:
        bonebeast_pos = locate_image(bonebeast_image, timeout=1.5, confidence=0.8)
        if bonebeast_pos:
            print(f"[ENEMY] BONEBEAST confirmado em {bonebeast_pos}! Pressionando \\ antes do ataque...")
            press_backslash(ser)  # PRESSIONA \ ANTES DO ATAQUE
            time.sleep(0.2)
            print(f"[ENEMY] Clicando no BONEBEAST...")
            if click_at_position(ser, bonebeast_pos[0], bonebeast_pos[1]):
                print("[ENEMY] Clique no BONEBEAST enviado com sucesso!")
                print("[ENEMY] Aguardando 8 segundos após atacar BONEBEAST...")
                time.sleep(8.0)  # DELAY BONEBEAST: 8 SEGUNDOS
                print("[ENEMY] Delay de 8s após BONEBEAST concluído!")
                return "bonebeast"
    except:
        pass
    
    # Verifica scarab - 6 SEGUNDOS
    try:
        scarab_pos = locate_image(scarab_image, timeout=1.5, confidence=0.8)
        if scarab_pos:
            print(f"[ENEMY] SCARAB confirmado em {scarab_pos}! Pressionando \\ antes do ataque...")
            press_backslash(ser)  # PRESSIONA \ ANTES DO ATAQUE
            time.sleep(0.2)
            print(f"[ENEMY] Clicando no SCARAB...")
            if click_at_position(ser, scarab_pos[0], scarab_pos[1]):
                print("[ENEMY] Clique no SCARAB enviado com sucesso!")
                print("[ENEMY] Aguardando 6 segundos após atacar SCARAB...")
                time.sleep(6.0)  # DELAY SCARAB: 6 SEGUNDOS
                print("[ENEMY] Delay de 6s após SCARAB concluído!")
                return "scarab"
    except:
        pass
    
    print("[ENEMY] Nenhum dos 3 inimigos específicos encontrado!")
    return None

def check_and_collect_gold(ser, gold_image):
    """
    Verifica se tem 100gp.png na tela.
    Se encontrar, aperta P e clica em cima do ouro.
    """
    try:
        gold_pos = locate_image(gold_image, timeout=1.0, confidence=0.6)
        if gold_pos:
            print(f"[GOLD] 100gp encontrado em {gold_pos}!")
            
            # Primeiro aperta P
            print("[GOLD] Pressionando tecla P...")
            if press_p(ser):
                print("[GOLD] Tecla P pressionada com sucesso!")
            else:
                print("[GOLD] ERRO ao pressionar P!")
                return False
            
            # Aguarda um pouco após pressionar P
            wait_exact(1.0, "Após pressionar P")
            
            # Depois clica no ouro
            print(f"[GOLD] Clicando no ouro em {gold_pos}...")
            if click_at_position(ser, gold_pos[0], gold_pos[1]):
                print("[GOLD] Ouro coletado com sucesso!")
                return True
            else:
                print("[GOLD] ERRO ao clicar no ouro!")
                return False
    except Exception as e:
        print(f"[GOLD] ERRO na coleta de ouro: {e}")
    
    return False

def gold_check_timer(ser, gold_image, last_gold_check):
    """
    Verifica se passou 2 minutos desde a última checagem de ouro.
    Se sim, procura por ouro e retorna novo timestamp.
    """
    current_time = time.time()
    if current_time - last_gold_check >= 120:  # 2 minutos = 120 segundos
        print("[TIMER] 2 minutos passaram, verificando ouro...")
        check_and_collect_gold(ser, gold_image)
        return current_time
    return last_gold_check

def battle_loop(ser, mummy_image, bonebeast_image, scarab_image):
    """
    Loop de batalha: encontra APENAS mummy, bonebeast e scarab e clica neles.
    Espera 8 segundos após cada clique nos inimigos específicos (agora integrado na função de clique).
    Quando não houver mais nenhum dos 3 inimigos, pressiona \\ e retorna.
    """
    battle_count = 0
    consecutive_no_enemies = 0
    
    print("[BATTLE] Iniciando loop de batalha...")
    
    while True:
        # Verifica healing durante a batalha
        check_and_heal(ser)
        
        # Tenta encontrar e clicar APENAS nos inimigos específicos
        enemy_clicked = find_and_click_specific_enemy(ser, mummy_image, bonebeast_image, scarab_image)
        
        if enemy_clicked:
            battle_count += 1
            consecutive_no_enemies = 0  # Reset contador
            print(f"[BATTLE] {enemy_clicked.upper()} atacado (#{battle_count})!")
            # Delay já foi aplicado na função find_and_click_specific_enemy
        else:
            consecutive_no_enemies += 1
            print(f"[BATTLE] Nenhum dos 3 inimigos específicos detectado ({consecutive_no_enemies}/2)")
            
            # Se não encontrou nenhum dos 3 inimigos por 2 verificações consecutivas, área está limpa
            if consecutive_no_enemies >= 2:
                print("[BATTLE] Nenhum mummy, bonebeast ou scarab encontrado após 2 verificações!")
                print("[BATTLE] Área limpa dos inimigos específicos!")
                print("[BATTLE] *** PRESSIONANDO \\ PARA FINALIZAR COMBATE ***")
                
                # GARANTIA MÁXIMA: Pressiona \ múltiplas vezes
                for i in range(3):
                    press_backslash(ser)
                    time.sleep(0.3)
                    print(f"[BATTLE] Backslash #{i+1} enviado")
                
                time.sleep(1.0)  # Pausa final após todos os backslashes
                print(f"[BATTLE] Batalha finalizada! Total de ataques: {battle_count}")
                print("[BATTLE] Avançando para próxima flag...")
                return  # Retorna para continuar com próxima flag
            
            # Espera um pouco antes de verificar novamente
            print("[BATTLE] Aguardando 2s antes de nova verificação...")
            time.sleep(2.0)  # Pausa um pouco mais entre verificações

def main_loop(ser):
    # Caminhos das flags na pasta flags/ (agora de 1 até 18)
    flag1 = os.path.abspath(os.path.join("..", "flags", "flag1.png"))
    flag2 = os.path.abspath(os.path.join("..", "flags", "flag2.png"))
    flag3 = os.path.abspath(os.path.join("..", "flags", "flag3.png"))
    flag4 = os.path.abspath(os.path.join("..", "flags", "flag4.png"))
    flag5 = os.path.abspath(os.path.join("..", "flags", "flag5.png"))
    flag6 = os.path.abspath(os.path.join("..", "flags", "flag6.png"))
    flag7 = os.path.abspath(os.path.join("..", "flags", "flag7.png"))
    flag8 = os.path.abspath(os.path.join("..", "flags", "flag8.png"))
    flag9 = os.path.abspath(os.path.join("..", "flags", "flag9.png"))
    flag10 = os.path.abspath(os.path.join("..", "flags", "flag10.png"))
    flag11 = os.path.abspath(os.path.join("..", "flags", "flag11.png"))
    flag12 = os.path.abspath(os.path.join("..", "flags", "flag12.png"))
    flag13 = os.path.abspath(os.path.join("..", "flags", "flag13.png"))
    flag14 = os.path.abspath(os.path.join("..", "flags", "flag14.png"))
    flag15 = os.path.abspath(os.path.join("..", "flags", "flag15.png"))
    flag16 = os.path.abspath(os.path.join("..", "flags", "flag16.png"))
    flag17 = os.path.abspath(os.path.join("..", "flags", "flag17.png"))
    flag18 = os.path.abspath(os.path.join("..", "flags", "flag18.png"))
    
    # Verifica se as flags existem
    print("[DEBUG] Verificando flags disponíveis...")
    flags_to_use = []
    for flag_num, flag_path in [
        ("Flag1", flag1), ("Flag2", flag2), ("Flag3", flag3), ("Flag4", flag4),
        ("Flag5", flag5), ("Flag6", flag6), ("Flag7", flag7), ("Flag8", flag8), 
        ("Flag9", flag9), ("Flag10", flag10), ("Flag11", flag11), ("Flag12", flag12),
        ("Flag13", flag13), ("Flag14", flag14), ("Flag15", flag15), ("Flag16", flag16),
        ("Flag17", flag17), ("Flag18", flag18)
    ]:
        if os.path.exists(flag_path):
            print(f"[DEBUG] {flag_num} encontrada: {flag_path}")
            flags_to_use.append((flag_num, flag_path))
        else:
            print(f"[WARNING] {flag_num} NÃO encontrada: {flag_path}")
    
    # Caminhos dos inimigos na pasta enemy/
    mummy = os.path.abspath(os.path.join("..", "enemy", "mummy.png"))
    bonebeast = os.path.abspath(os.path.join("..", "enemy", "bonebeast.png"))
    scarab = os.path.abspath(os.path.join("..", "enemy", "scarab.png"))
    
    # Verifica se os inimigos existem
    print("[DEBUG] Verificando inimigos disponíveis...")
    for enemy_name, enemy_path in [("Mummy", mummy), ("Bonebeast", bonebeast), ("Scarab", scarab)]:
        if os.path.exists(enemy_path):
            print(f"[DEBUG] {enemy_name} encontrado: {enemy_path}")
        else:
            print(f"[ERROR] {enemy_name} NÃO encontrado: {enemy_path}")
    
    # Caminho do ouro na pasta scripts/
    gold = os.path.abspath("100gp.png")
    
    # Timer para verificação de ouro a cada 2 minutos
    last_gold_check = time.time()
    
    cycle = 1
    while True:
        print("\n" + "="*50)
        print(f"MUMMY CYCLE #{cycle} - {len(flags_to_use)} FLAGS - MONITORAMENTO ATIVO")
        print("="*50)
        try:
            for flag_name, flag_path in flags_to_use:
                current_phase = f"processando {flag_name}"
                
                # Loop para retomar ação interrompida
                action_completed = False
                while not action_completed:
                    print(f"\n[PASSO] {flag_name}...")
                    print(f"[DEBUG] Procurando: {flag_path}")
                    
                    # Verifica ouro a cada 2 minutos
                    last_gold_check = gold_check_timer(ser, gold, last_gold_check)
                    
                    # Tenta localizar a flag até 5 vezes com confidence variado
                    pos = None
                    flag_found = False
                    for attempt in range(5):
                        # Durante a busca por flags, também monitora inimigos E healing
                        enemy_found = quick_enemy_check(mummy, bonebeast, scarab)
                        if enemy_found:
                            enemy_name, enemy_pos = enemy_found
                            print(f"[INTERRUPT] {enemy_name.upper()} detectado durante busca de {flag_name}!")
                            print(f"[INTERRUPT] Pressionando \\ antes de atacar {enemy_name}...")
                            press_backslash(ser)
                            time.sleep(0.2)
                            if click_at_position(ser, enemy_pos[0], enemy_pos[1]):
                                print(f"[INTERRUPT] {enemy_name.upper()} atacado durante busca!")
                                # Delay específico baseado no inimigo
                                if enemy_name == "mummy":
                                    delay_time = 5.0
                                elif enemy_name == "bonebeast":
                                    delay_time = 8.0
                                elif enemy_name == "scarab":
                                    delay_time = 6.0
                                print(f"[INTERRUPT] Aguardando {delay_time}s após atacar {enemy_name}...")
                                time.sleep(delay_time)
                                print(f"[INTERRUPT] *** AÇÃO INTERROMPIDA! RETOMANDO BUSCA DE {flag_name} ***")
                                # Reinicia a busca da flag do zero
                                break
                        
                        # Também verifica healing durante busca
                        check_and_heal(ser)
                        
                        # Usa confidence 0.8 para melhor precisão nas flags, depois reduz
                        confidence = 0.8 if attempt < 2 else 0.7 if attempt < 4 else 0.6
                        print(f"[DEBUG] Tentativa {attempt + 1}/5 com confidence {confidence}")
                        pos = locate_image(flag_path, timeout=10.0, confidence=confidence)
                        if pos:
                            print(f"[{flag_name}] Detectada na tentativa {attempt + 1} com confidence {confidence}")
                            flag_found = True
                            break
                        print(f"[RETRY] Tentativa {attempt + 1}/5 para {flag_name} (confidence {confidence})")
                        wait_exact(1.0)
                    
                    if not flag_found or not pos: 
                        print(f"[ERRO] {flag_name} não encontrada após 5 tentativas!")
                        print(f"[DEBUG] Pulando para próxima flag...")
                        action_completed = True  # Sai do loop de retomada
                        break  # Sai do while action_completed
                    
                    print(f"[{flag_name}] Encontrada em {pos}, validando posição...")
                    
                    # Validação adicional: re-detecta a flag antes de clicar
                    print(f"[{flag_name}] Re-validando detecção...")
                    validation_pos = locate_image(flag_path, timeout=3.0, confidence=0.7)
                    if validation_pos:
                        # Se a re-detecção está próxima da original (até 10px de diferença)
                        distance = abs(pos[0] - validation_pos[0]) + abs(pos[1] - validation_pos[1])
                        if distance <= 10:
                            print(f"[{flag_name}] Posição validada! Distância: {distance}px")
                            pos = validation_pos  # Usa a posição mais recente
                        else:
                            print(f"[{flag_name}] Posições muito diferentes! Original: {pos}, Nova: {validation_pos}")
                            pos = validation_pos  # Usa a nova posição
                    else:
                        print(f"[{flag_name}] Re-validação falhou, usando posição original: {pos}")
                    
                    # Tenta clicar na flag até 3 vezes com pausa maior
                    click_success = False
                    for click_attempt in range(3):
                        # Move o mouse para a posição antes de clicar
                        print(f"[{flag_name}] Tentativa de clique {click_attempt + 1}/3 em {pos}")
                        if click_at_position(ser, pos[0], pos[1]):
                            print(f"[{flag_name}] Clique bem-sucedido!")
                            click_success = True
                            break
                        print(f"[RETRY] Falha no clique, tentando novamente...")
                        wait_exact(1.5)
                    
                    if not click_success:
                        print(f"[ERRO] Falha ao clicar em {flag_name} após 3 tentativas!")
                        print(f"[{flag_name}] *** FALHA NO CLIQUE! RETOMANDO DO INÍCIO ***")
                        continue  # Retoma do início desta flag
                    
                    print(f"[{flag_name}] Clique enviado com sucesso!")
                    
                    # DELAY FIXO DE 15 SEGUNDOS após cada flag - COM MONITORAMENTO  
                    was_interrupted = monitored_wait(ser, 15.0, f"Aguardando 15s após {flag_name}", mummy, bonebeast, scarab, f"delay pós-{flag_name}")
                    
                    if was_interrupted:
                        print(f"[{flag_name}] *** DELAY INTERROMPIDO! RETOMANDO DO INÍCIO ***")
                        continue  # Retoma do início desta flag
                    
                    # Verifica ouro antes de iniciar batalha
                    last_gold_check = gold_check_timer(ser, gold, last_gold_check)
                    
                    # Inicia loop de batalha com os 3 inimigos específicos
                    print(f"[{flag_name}] Iniciando verificação de mummy, bonebeast e scarab...")
                    battle_loop(ser, mummy, bonebeast, scarab)
                    
                    # GARANTIA: Pressiona \ novamente após cada flag completa
                    print(f"[{flag_name}] *** GARANTINDO \\ FINAL ***")
                    press_backslash(ser)
                    time.sleep(0.5)
                    
                    print(f"[{flag_name}] Completada! Próxima flag...")
                    
                    # Verifica ouro após batalha
                    last_gold_check = gold_check_timer(ser, gold, last_gold_check)
                    
                    action_completed = True  # Marca como completada para seguir para próxima flag
                    # Move o mouse para a posição antes de clicar
                    print(f"[{flag_name}] Tentativa de clique {click_attempt + 1}/3 em {pos}")
                    if click_at_position(ser, pos[0], pos[1]):
                        print(f"[{flag_name}] Clique bem-sucedido!")
                        click_success = True
                        break
                    print(f"[RETRY] Falha no clique, tentando novamente...")
                    wait_exact(1.5)
                
                if not click_success:
                    print(f"[ERRO] Falha ao clicar em {flag_name} após 3 tentativas!")
                    # Tenta uma vez mais com re-detecção
                    print(f"[{flag_name}] Tentando re-detectar para último clique...")
                    pos = locate_image(flag_path, timeout=5.0, confidence=0.5)
                    if pos:
                        click_at_position(ser, pos[0], pos[1])
                    continue
                
                print(f"[{flag_name}] Clique enviado com sucesso!")
                
                # DELAY FIXO DE 15 SEGUNDOS após cada flag - COM MONITORAMENTO
                monitored_wait(ser, 15.0, f"Aguardando 15s após {flag_name}", mummy, bonebeast, scarab, f"delay pós-{flag_name}")
                
                # Verifica ouro antes de iniciar batalha
                last_gold_check = gold_check_timer(ser, gold, last_gold_check)
                
                # Inicia loop de batalha com os 3 inimigos específicos
                print(f"[{flag_name}] Iniciando verificação de mummy, bonebeast e scarab...")
                battle_loop(ser, mummy, bonebeast, scarab)
                
                # GARANTIA: Pressiona \ novamente após cada flag completa
                print(f"[{flag_name}] *** GARANTINDO \\ FINAL ***")
                press_backslash(ser)
                time.sleep(0.5)
                
                print(f"[{flag_name}] Completada! Próxima flag...")
                
                # Verifica ouro após batalha
                last_gold_check = gold_check_timer(ser, gold, last_gold_check)
            
            print(f"\n[OK] Mummy Cycle #{cycle} completo! ({len(flags_to_use)} flags processadas)")
            cycle += 1
            monitored_wait(ser, 3.0, "Antes de reiniciar ciclo", mummy, bonebeast, scarab, f"intervalo entre ciclos #{cycle-1} e #{cycle}")
            
        except KeyboardInterrupt:
            print("\n[STOP] Ctrl+C")
            break
        except Exception as e:
            print(f"\n[ERRO] {e}")
            wait_exact(5.0)

def main():
    print(f"\n[SERIAL] Conectando {COM_PORT} @ {BAUD_RATE}...")
    print("MUMMY BOT - 3 Inimigos, 18 Flags - MONITORAMENTO + HEALING")
    print("Configuração:")
    print("- Inimigos: mummy.png, bonebeast.png, scarab.png")
    print("- Flags: 1 até 18 (18 flags por ciclo)")
    print("- Delay após flag: 15 segundos")
    print("- DELAYS ESPECÍFICOS POR INIMIGO:")
    print("  * MUMMY: 5 segundos após ataque")
    print("  * SCARAB: 6 segundos após ataque")  
    print("  * BONEBEAST: 8 segundos após ataque")
    print("- Coleta de ouro a cada 2 minutos")
    print("- BACKSLASH GARANTIDO após cada combate")
    print("- MONITORAMENTO CONTÍNUO de inimigos")
    print("  * Durante delays, busca por flags, esperas")
    print("  * Para e ataca inimigos imediatamente")
    print("  * Retoma atividade anterior após ataque")
    print("- SISTEMA DE HEALING INTEGRADO")
    print("  * HP médio (cor amarela) → Tecla 3")
    print("  * Verifica HP continuamente")
    print("  * Healing durante todas as atividades")
    print("- Debug melhorado para detecção de flags")
    input("ENTER para iniciar...")
    try:
        with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"[OK] Conectado em {COM_PORT}")
            print("[SERIAL] Aguardando Arduino...")
            wait_exact(2.0)
            ser.reset_input_buffer()
            print("[OK] Arduino pronto!\n")
            print(f"[HEALING] Sistema de healing {'ATIVADO' if HEALING_ENABLED else 'DESATIVADO'}")
            if HEALING_ENABLED:
                print(f"[HEALING] Região do HP: {HP_REGION}")
                print(f"[HEALING] HP médio → Tecla 3")
            main_loop(ser)
    except serial.SerialException as e:
        print(f"[ERRO] Serial: {e}")
    except KeyboardInterrupt:
        print("\n[STOP] Programa interrompido")

if __name__ == "__main__":
    main()