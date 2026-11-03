import time
from collections import deque

# Usamos estos códigos ANSI para darle color a la consola en el menú
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# Esta función nos sirve para encerrar los mensajes en un cuadro con borde rojo, por est´tica
def print_red_box(text_lines):
    # Acá quitamos los colores temporalmente para poder calcular bien el ancho del cuadro
    plain_lines = []
    for line in text_lines:
        plain = line.replace(RED, "").replace(YELLOW, "").replace(RESET, "")
        plain_lines.append(plain)
        
    max_len = max(len(p) for p in plain_lines)
    border = "+" + "-" * (max_len + 2) + "+"
    print(RED + border + RESET)
    
    # Imprimimos cada línea dentro del marco rojo
    for original_line, plain_line in zip(text_lines, plain_lines):
        padding = " " * (max_len - len(plain_line))
        print(RED + "| " + RESET + original_line + padding + RED + " |" + RESET)
        
    print(RED + border + RESET)


# Esta clase nos guarda el historial de las últimas cosas que hizo el Kernel con un máximo de 10
class EventLogger:
    def __init__(self, max_events=10):
        self.logs = []
        self.max_events = max_events

    # Guarda un mensaje con la hora exacta
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        
        # Si nos pasamos de 10 eventos, borramos el más viejo
        if len(self.logs) > self.max_events:
            self.logs.pop(0)

    # Este comando nos imprime los eventos guardados en la pantalla
    def show_logs(self):
        lines = [YELLOW + "BITÁCORA DE ÚLTIMOS EVENTOS DEL KERNEL" + RESET]
        if not self.logs:
            lines.append(YELLOW + "(No hay eventos registrados todavía)" + RESET)
        else:
            for log in self.logs:
                lines.append(YELLOW + log + RESET)
        print()
        print_red_box(lines)


# La clase PCB representa a cada proceso (como su ficha de datos)
class PCB:
    def __init__(self, pid, size_mb, burst_time):
        self.pid = pid                      # En este nos muestra el número identificador único, PID
        self.state = "NUEVO"                # Observamos que el estado en el que está el proceso (NUEVO, LISTO, EJECUCION, BLOQUEADO, TERMINADO)
        self.size_mb = size_mb              # Nos muestra cuánta RAM ocupa en tamaño de MB
        self.burst_time = burst_time        # Este representa cuanto es el tiempo total que necesita de CPU
        self.remaining_time = burst_time    # El tiempo de CPU que le falta para terminar
        self.held_resources = []            # Los recursos que tiene prestados

    # Nos sirve para imprimir la información del proceso de forma bonita
    def __str__(self):
        return f"[PID: {self.pid:03d} | Estado: {self.state:<9} | RAM: {self.size_mb:2d} MB | CPU Restante: {self.remaining_time:2d}s]"


# Aquí controlamos la memoria RAM simulada, es decir el límite máximo es 100 MB tal como lo indicaron las instrucciones del ingeniero
class MemoryManager:
    TOTAL_MEMORY = 100

    def __init__(self, logger):
        self.used_memory = 0  # Esta es la RAM ocupada actualmente
        self.logger = logger

    # Este comando revisa si hay espacio en la RAM para meter un nuevo proceso
    def allocate(self, pcb):
        if self.used_memory + pcb.size_mb <= self.TOTAL_MEMORY:
            self.used_memory += pcb.size_mb
            pcb.state = "LISTO"
            msg = f"MEMORIA: Proceso PID {pcb.pid} asignado ({pcb.size_mb} MB). Uso RAM: {self.used_memory}/{self.TOTAL_MEMORY} MB."
            print_red_box([YELLOW + f"Intentando ingresar Proceso PID: {pcb.pid}" + RESET, YELLOW + msg + RESET])
            self.logger.log(msg)
            return True
        else:
            # Si no cabe, viene y tira error de desbordamiento
            msg = f"ERROR OUT OF MEMORY: Proceso PID {pcb.pid} rechazado. Pide {pcb.size_mb} MB, disponible: {self.TOTAL_MEMORY - self.used_memory} MB."
            print_red_box([YELLOW + f"Intentando ingresar Proceso PID: {pcb.pid}" + RESET, YELLOW + msg + RESET])
            self.logger.log(msg)
            return False

    # Aqui es cuando libera la RAM cuando un proceso termina
    def free(self, pcb):
        self.used_memory -= pcb.size_mb
        msg = f"MEMORIA: Proceso PID {pcb.pid} liberó {pcb.size_mb} MB. Uso RAM: {self.used_memory}/{self.TOTAL_MEMORY} MB."
        print_red_box([YELLOW + msg + RESET])
        self.logger.log(msg)


# Este es el Semáforo Binario para controlar que dos procesos no entren a la vez a la misma variable
class BinarySemaphore:
    def __init__(self, logger):
        self.value = 1  # El No. 1 significa libre y 0 significa ocupado
        self.waiting_queue = deque() # Cola donde esperan los procesos si está ocupado
        self.logger = logger
        self.current_owner = None

    # Función wait(): Indica que el proceso pide permiso para entrar a la zona crítica
    def wait(self, pcb):
        if self.value == 1:
            self.value = 0 
            self.current_owner = pcb.pid
            msg = f"CONCURRENCIA: Proceso PID {pcb.pid} ejecutó wait() e INGRESÓ a la Sección Crítica."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return True
        else:
            # Si estaba ocupado, mandamos el proceso a la cola de espera
            pcb.state = "BLOQUEADO"
            self.waiting_queue.append(pcb)
            msg = f"CONCURRENCIA: Sección Crítica ocupada por PID {self.current_owner}. PID {pcb.pid} BLOQUEADO y enviado a cola del semáforo."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return False

    # Función signal(): El proceso sale de la zona crítica y deja pasar al siguiente
    def signal(self):
        if self.waiting_queue:
            # Sacamos al siguiente de la cola de espera y lo ponemos en listo
            next_pcb = self.waiting_queue.popleft()
            next_pcb.state = "LISTO"
            self.current_owner = next_pcb.pid
            msg = f"CONCURRENCIA: Proceso PID {next_pcb.pid} DESBLOQUEADO de la cola y movido a la Cola de Listos."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return next_pcb
        else:
            self.value = 1 # Si no hay nadie esperando, la zona crítica queda libre
            self.current_owner = None
            msg = "CONCURRENCIA: Sección Crítica liberada exitosamente."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return None


# Aquí simulamos y resolvemos el problema del choque de recursos, el famoso Deadlock.
class DeadlockManager:
    def __init__(self, logger):
        self.logger = logger
        self.resource1 = None
        self.resource2 = None
        self.is_deadlocked = False

    # Forzamos una espera circular. El proceso A tiene R1 y pide R2, el proceso B tiene R2 y pide R1
    def force_circular_wait(self):
        self.resource1 = 101
        self.resource2 = 102
        self.is_deadlocked = True

        lines = [
            YELLOW + "DETECCIÓN DE INTERBLOQUEO (DEADLOCK)" + RESET,
            YELLOW + "Asignación actual de recursos:" + RESET,
            YELLOW + " - Proceso A (PID 101): Retiene Recurso 1 y solicita Recurso 2." + RESET,
            YELLOW + " - Proceso B (PID 102): Retiene Recurso 2 y solicita Recurso 1." + RESET,
            YELLOW + "ALERTA: Espera circular confirmada entre PID 101 y PID 102." + RESET
        ]
        print_red_box(lines)
        self.logger.log("DEADLOCK DETECTADO: Espera circular confirmada entre PID 101 y PID 102.")

    # Eliminamos el traba matando o abortando a uno de los dos procesos
    def resolve(self, victim_pid):
        if not self.is_deadlocked:
            print_red_box([YELLOW + "Deadlock: Actualmente no hay ningún interbloqueo activo." + RESET])
            return

        if victim_pid == 101:
            self.resource1 = None
            self.is_deadlocked = False
            msg = "DEADLOCK RESUELTO: Se abortó Proceso A (PID 101). Recurso 1 liberado. Proceso B (PID 102) puede continuar."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
        elif victim_pid == 102:
            self.resource2 = None
            self.is_deadlocked = False
            msg = "DEADLOCK RESUELTO: Se abortó Proceso B (PID 102). Recurso 2 liberado. Proceso A (PID 101) puede continuar."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
        else:
            print_red_box([YELLOW + "PID no válido. Elige entre el 101 o 102." + RESET])


# Esta es la clase principal que junta todos los módulos del Kernel
class KernelSimulator:
    def __init__(self, quantum=3):
        self.quantum = quantum              # Asignamos el Quantum de 3 segundos obligatorio
        self.logger = EventLogger()         # Esta es la bitácora
        self.memory = MemoryManager(self.logger) # Memoria
        self.semaphore = BinarySemaphore(self.logger) # Concurrencia
        self.deadlock_mgr = DeadlockManager(self.logger) # Deadlocks
        self.ready_queue = deque()          # Cola de Listos
        self.pid_counter = 1                # Contador para asignar PIDs automáticamente

    # Crea el proceso y lo mete a la cola si hay memoria suficiente
    def create_process(self, size_mb, burst_time):
        pcb = PCB(self.pid_counter, size_mb, burst_time)
        if self.memory.allocate(pcb):
            self.ready_queue.append(pcb)
            self.logger.log(f"PROCESO: PID {pcb.pid} agregado a la Cola de Listos.")
            self.pid_counter += 1
            return pcb
        return None

    # Algoritmo de planificación Round Robin con turnos de 3 segundos
    def run_round_robin(self):
        if not self.ready_queue:
            print_red_box([YELLOW + "[CPU] No hay procesos listos en la cola para ejecutar." + RESET])
            return

        print_red_box([YELLOW + f"EJECUTANDO PLANIFICADOR ROUND ROBIN (Quantum = {self.quantum}s)" + RESET])

        while self.ready_queue:
            # Sacamos al primero que llegó a la cola (FIFO)
            current = self.ready_queue.popleft()
            current.state = "EJECUCION"
            
            # Le damos como máximo el tiempo del quantum, 3 segundos, como en el caso de Robin
            exec_time = min(self.quantum, current.remaining_time)
            current.remaining_time -= exec_time

            # Si al proceso todavía le queda tiempo, se hace un cambio de contexto y vuelve al final de la cola
            if current.remaining_time > 0:
                current.state = "LISTO"
                self.ready_queue.append(current)
                msg = f"PLANIFICADOR: Quantum de {self.quantum}s agotado. Cambio de contexto para PID {current.pid}."
                print_red_box([YELLOW + f"CPU: Ejecutando PID {current.pid} por {exec_time}s..." + RESET, YELLOW + msg + RESET])
                self.logger.log(msg)
            else:
                # Si terminó todo su tiempo, lo marcamos como terminado y liberamos su RAM
                current.state = "TERMINADO"
                msg = f"PLANIFICADOR: PID {current.pid} completó su ejecución."
                print_red_box([YELLOW + f"CPU: Ejecutando PID {current.pid} por {exec_time}s..." + RESET, YELLOW + msg + RESET])
                self.logger.log(msg)
                self.memory.free(current)


# Menú principal interactivo de la consola que nos muestra lo que deseemos hacer
def main():
    kernel = KernelSimulator(quantum=3)

    while True:
        print()
        
        # Imprimimos el panel principal con tus datos y el nombre del profesor
        print_red_box([
            YELLOW + "SIMULADOR DE KERNEL DE SISTEMAS OPERATIVOS 1 - PANEL DE CONTROL" + RESET,
            YELLOW + "Estudiante: Cristian Josué Cruz López | Carné: 7690-24-7788" + RESET,
            YELLOW + "Catedrático: Ing. Julio Gomez" + RESET,
            RED + "------------------------------------------------------------------" + RESET,
            RED + "1. " + YELLOW + "Crear e Ingresar Proceso" + RESET,
            RED + "2. " + YELLOW + "Mostrar Estado del Sistema (RAM y Cola de Listos)" + RESET,
            RED + "3. " + YELLOW + "Ejecutar Planificador Round Robin (q=3)" + RESET,
            RED + "4. " + YELLOW + "Demostrar Concurrencia (Semáforo Binario)" + RESET,
            RED + "5. " + YELLOW + "Forzar Condición de Deadlock" + RESET,
            RED + "6. " + YELLOW + "Resolver Deadlock (Abortar Proceso)" + RESET,
            RED + "7. " + YELLOW + "Ver Bitácora de Últimos Eventos (Logs)" + RESET,
            RED + "8. " + YELLOW + "Salir" + RESET
        ])
        
        opcion = input("\nSeleccione una opción (1-8): ")

        if opcion == "1":
            try:
                ram = int(input("Ingrese tamaño del proceso en RAM (MB): "))
                rafaga = int(input("Ingrese tiempo de ráfaga de CPU (segundos): "))
                kernel.create_process(ram, rafaga)
            except ValueError:
                print_red_box([YELLOW + "Error: Escribe números enteros válidos." + RESET])

        elif opcion == "2":
            lines = [YELLOW + f"Uso de Memoria RAM: {kernel.memory.used_memory}/100 MB" + RESET, YELLOW + "Procesos en Cola de Listos:" + RESET]
            if not kernel.ready_queue:
                lines.append(YELLOW + " (Cola vacía)" + RESET)
            else:
                for p in kernel.ready_queue:
                    lines.append(YELLOW + f" - {p}" + RESET)
            print_red_box(lines)

        elif opcion == "3":
            kernel.run_round_robin()

        elif opcion == "4":
            p1 = PCB(901, 10, 5)
            p2 = PCB(902, 10, 5)
            
            print_red_box([YELLOW + "1. PID 901 ejecuta wait()" + RESET])
            kernel.semaphore.wait(p1)
            
            print_red_box([YELLOW + "2. PID 902 ejecuta wait() al mismo tiempo" + RESET])
            kernel.semaphore.wait(p2)
            
            print_red_box([YELLOW + "3. PID 901 sale de la Sección Crítica y ejecuta signal()" + RESET])
            unblocked = kernel.semaphore.signal()
            if unblocked:
                kernel.ready_queue.append(unblocked)

        elif opcion == "5":
            kernel.deadlock_mgr.force_circular_wait()

        elif opcion == "6":
            try:
                victim = int(input("Ingrese el PID a abortar para resolver el Deadlock (101 o 102): "))
                kernel.deadlock_mgr.resolve(victim)
            except ValueError:
                print_red_box([YELLOW + "Error: PID no válido." + RESET])

        elif opcion == "7":
            kernel.logger.show_logs()

        elif opcion == "8":
            print_red_box([YELLOW + "Saliendo del Simulador de Kernel..." + RESET])
            break
        else:
            print_red_box([YELLOW + "Opción no válida. Intenta otra vez." + RESET])

if __name__ == "__main__":
    main()