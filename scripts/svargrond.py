# amazom.py - Automacao de batalha com deteccao de imagem e Arduino
import os, time, pyautogui as pg, serial, ctypes
from typing import Optional, Tuple

print("="*50)
print("AMAZOM - Automacao com Arduino HID")
print("="*50)

COM_PORT = "COM11"  # Porta atualizada conforme disponível
BAUD_RATE = 9600
LOCATE_TIMEOUT = 20.0  # Aumentado para melhor detecção de flags
CONFIDENCE = 0.8  # Aumentado para melhor precisão na detecção

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

def find_and_click_specific_enemy(ser, mammoth_image, winterwolf_image, badger_image):
    """
    Procura APENAS por mammoth, winterwolf e badger na tela e clica no primeiro encontrado.
    Usa confidence alto para garantir que é realmente o animal correto.
    Retorna o nome do inimigo se encontrou e clicou, None caso contrário.
    """
    print("[ENEMY] Procurando APENAS mammoth, winterwolf e badger...")
    
    # Verifica mammoth primeiro - confidence alto para precisão
    try:
        mammoth_pos = locate_image(mammoth_image, timeout=1.5, confidence=0.8)
        if mammoth_pos:
            print(f"[ENEMY] MAMMOTH confirmado em {mammoth_pos}! Clicando...")
            if click_at_position(ser, mammoth_pos[0], mammoth_pos[1]):
                print("[ENEMY] Clique no MAMMOTH enviado com sucesso!")
                return "mammoth"
    except:
        pass
    
    # Verifica winterwolf
    try:
        winterwolf_pos = locate_image(winterwolf_image, timeout=1.5, confidence=0.8)
        if winterwolf_pos:
            print(f"[ENEMY] WINTERWOLF confirmado em {winterwolf_pos}! Clicando...")
            if click_at_position(ser, winterwolf_pos[0], winterwolf_pos[1]):
                print("[ENEMY] Clique no WINTERWOLF enviado com sucesso!")
                return "winterwolf"
    except:
        pass
    
    # Verifica badger
    try:
        badger_pos = locate_image(badger_image, timeout=1.5, confidence=0.8)
        if badger_pos:
            print(f"[ENEMY] BADGER confirmado em {badger_pos}! Clicando...")
            if click_at_position(ser, badger_pos[0], badger_pos[1]):
                print("[ENEMY] Clique no BADGER enviado com sucesso!")
                return "badger"
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

def battle_loop(ser, mammoth_image, winterwolf_image, badger_image):
    """
    Loop de batalha: encontra APENAS mammoth, winterwolf e badger e clica neles.
    Espera 5 segundos após cada clique nos inimigos específicos.
    Quando não houver mais nenhum dos 3 inimigos, pressiona \\ e retorna.
    """
    battle_count = 0
    consecutive_no_enemies = 0
    
    while True:
        # Tenta encontrar e clicar APENAS nos inimigos específicos
        enemy_clicked = find_and_click_specific_enemy(ser, mammoth_image, winterwolf_image, badger_image)
        
        if enemy_clicked:
            battle_count += 1
            consecutive_no_enemies = 0  # Reset contador
            print(f"[BATTLE] {enemy_clicked.upper()} atacado (#{battle_count})!")
            print(f"[BATTLE] Aguardando 3 segundos após clique no {enemy_clicked}...")
            wait_exact(3.0, f"Delay após atacar {enemy_clicked}")
        else:
            consecutive_no_enemies += 1
            print(f"[BATTLE] Nenhum dos 3 inimigos específicos detectado ({consecutive_no_enemies}/1)")
            
            # Se não encontrou nenhum dos 3 inimigos na primeira verificação, área está limpa
            if consecutive_no_enemies >= 1:
                print("[BATTLE] Nenhum mammoth, winterwolf ou badger encontrado na primeira verificação!")
                print("[BATTLE] Área limpa dos inimigos específicos!")
                print("[BATTLE] Pressionando \\ para finalizar...")
                press_backslash(ser)
                wait_exact(0.5, "Após pressionar \\")
                print(f"[BATTLE] Batalha finalizada! Total de ataques: {battle_count}")
                print("[BATTLE] Avançando para próxima flag...")
                return  # Retorna para continuar com próxima flag
            
            # Espera um pouco antes de verificar novamente
            wait_exact(1.0, "Aguardando antes de nova verificação dos 3 inimigos")

def main_loop(ser):
    # Caminhos das flags na pasta flags/
    flag1 = os.path.abspath(os.path.join("..", "flags", "flag1.png"))
    flag2 = os.path.abspath(os.path.join("..", "flags", "flag2.png"))
    flag3 = os.path.abspath(os.path.join("..", "flags", "flag3.png"))
    flag4 = os.path.abspath(os.path.join("..", "flags", "flag4.png"))
    flag5 = os.path.abspath(os.path.join("..", "flags", "flag5.png"))
    flag6 = os.path.abspath(os.path.join("..", "flags", "flag6.png"))
    flag7 = os.path.abspath(os.path.join("..", "flags", "flag7.png"))
    
    # Caminhos dos inimigos na pasta enemy/ (usando amazon.png como fallback se outros não existirem)
    mammoth = os.path.abspath(os.path.join("..", "enemy", "amazon.png"))  # Temporário
    winterwolf = os.path.abspath(os.path.join("..", "enemy", "amazon.png"))  # Temporário  
    badger = os.path.abspath(os.path.join("..", "enemy", "amazon.png"))  # Temporário
    
    # Caminho do ouro na pasta scripts/
    gold = os.path.abspath("100gp.png")
    
    flags = [
        ("Flag1", flag1),
        ("Flag2", flag2),
        ("Flag3", flag3),
        ("Flag4", flag4),
        ("Flag5", flag5),
        ("Flag6", flag6),
        ("Flag7", flag7)
    ]
    
    # Timer para verificação de ouro a cada 2 minutos
    last_gold_check = time.time()
    
    cycle = 1
    while True:
        print("\n" + "="*50)
        print(f"CICLO #{cycle}")
        print("="*50)
        try:
            for flag_name, flag_path in flags:
                print(f"\n[PASSO] {flag_name}...")
                
                # Verifica ouro a cada 2 minutos
                last_gold_check = gold_check_timer(ser, gold, last_gold_check)
                
                # Tenta localizar a flag até 5 vezes com confidence alta
                pos = None
                for attempt in range(5):
                    # Usa confidence 0.8 para melhor precisão nas flags
                    confidence = 0.8 if attempt < 3 else 0.7  # Confidence mais alto para flags
                    pos = locate_image(flag_path, timeout=15.0, confidence=confidence)
                    if pos:
                        print(f"[{flag_name}] Detectada na tentativa {attempt + 1} com confidence {confidence}")
                        break
                    print(f"[RETRY] Tentativa {attempt + 1}/5 para {flag_name} (confidence {confidence})")
                    wait_exact(2.0)
                
                if not pos: 
                    print(f"[ERRO] {flag_name} não encontrada após 5 tentativas!")
                    continue
                
                print(f"[{flag_name}] Encontrada em {pos}, validando posição...")
                
                # Validação adicional: re-detecta a flag antes de clicar
                print(f"[{flag_name}] Re-validando detecção...")
                validation_pos = locate_image(flag_path, timeout=3.0, confidence=0.8)
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
                    # Tenta uma vez mais com re-detecção
                    print(f"[{flag_name}] Tentando re-detectar para último clique...")
                    pos = locate_image(flag_path, timeout=5.0, confidence=0.4)
                    if pos:
                        click_at_position(ser, pos[0], pos[1])
                    continue
                
                print(f"[{flag_name}] Clique enviado com sucesso!")
                
                # Delays específicos por flag
                flag_delays = {
                    "Flag1": 20.0,  # 20 segundos
                    "Flag2": 27.0,  # 27 segundos
                    "Flag3": 23.0,  # 23 segundos  
                    "Flag4": 18.0,  # 18 segundos
                    "Flag5": 20.0,  # 20 segundos
                    "Flag6": 15.0,  # 15 segundos
                    "Flag7": 10.0   # 10 segundos
                }
                delay_time = flag_delays.get(flag_name, 20.0)
                wait_exact(delay_time, f"Aguardando após {flag_name}")
                
                # Verifica ouro antes de iniciar batalha
                last_gold_check = gold_check_timer(ser, gold, last_gold_check)
                
                # Inicia loop de batalha
                print(f"[{flag_name}] Iniciando verificação de inimigos...")
                battle_loop(ser, mammoth, winterwolf, badger)
                
                print(f"[{flag_name}] Completada! Próxima flag...")
                
                # Verifica ouro após batalha
                last_gold_check = gold_check_timer(ser, gold, last_gold_check)
            
            print(f"\n[OK] Ciclo #{cycle} completo!")
            cycle += 1
            wait_exact(3.0, "Antes de reiniciar")
            
        except KeyboardInterrupt:
            print("\n[STOP] Ctrl+C")
            break
        except Exception as e:
            print(f"\n[ERRO] {e}")
            wait_exact(5.0)

def main():
    print(f"\n[SERIAL] Conectando {COM_PORT} @ {BAUD_RATE}...")
    input("ENTER para iniciar...")
    try:
        with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"[OK] Conectado em {COM_PORT}")
            print("[SERIAL] Aguardando Arduino...")
            wait_exact(2.0)
            ser.reset_input_buffer()
            print("[OK] Arduino pronto!\n")
            main_loop(ser)
    except serial.SerialException as e:
        print(f"[ERRO] Serial: {e}")
    except KeyboardInterrupt:
        print("\n[STOP] Programa interrompido")

if __name__ == "__main__":
    main()