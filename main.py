import time
from collections import deque

RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def print_red_box(text_lines):
    # Calculamos la longitud sin tomar en cuenta los códigos de color ANSI
    plain_lines = []
    for line in text_lines:
        plain = line.replace(RED, "").replace(YELLOW, "").replace(RESET, "")
        plain_lines.append(plain)
        
    max_len = max(len(p) for p in plain_lines)
    border = "+" + "-" * (max_len + 2) + "+"
    print(RED + border + RESET)
    
    for original_line, plain_line in zip(text_lines, plain_lines):
        padding = " " * (max_len - len(plain_line))
        print(RED + "| " + RESET + original_line + padding + RED + " |" + RESET)
        
    print(RED + border + RESET)


class EventLogger:
    def __init__(self, max_events=10):
        self.logs = []
        self.max_events = max_events

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        if len(self.logs) > self.max_events:
            self.logs.pop(0)

    def show_logs(self):
        lines = [YELLOW + "BITÁCORA DE ÚLTIMOS EVENTOS DEL KERNEL" + RESET]
        if not self.logs:
            lines.append(YELLOW + "(No hay eventos registrados)" + RESET)
        else:
            for log in self.logs:
                lines.append(YELLOW + log + RESET)
        print()
        print_red_box(lines)


class PCB:
    def __init__(self, pid, size_mb, burst_time):
        self.pid = pid
        self.state = "NUEVO"
        self.size_mb = size_mb
        self.burst_time = burst_time
        self.remaining_time = burst_time
        self.held_resources = []

    def __str__(self):
        return f"[PID: {self.pid:03d} | Estado: {self.state:<9} | RAM: {self.size_mb:2d} MB | CPU Restante: {self.remaining_time:2d}s]"


class MemoryManager:
    TOTAL_MEMORY = 100

    def __init__(self, logger):
        self.used_memory = 0
        self.logger = logger

    def allocate(self, pcb):
        if self.used_memory + pcb.size_mb <= self.TOTAL_MEMORY:
            self.used_memory += pcb.size_mb
            pcb.state = "LISTO"
            msg = f"MEMORIA: Proceso PID {pcb.pid} asignado ({pcb.size_mb} MB). Uso RAM: {self.used_memory}/{self.TOTAL_MEMORY} MB."
            print_red_box([YELLOW + f"Intentando ingresar Proceso PID: {pcb.pid}" + RESET, YELLOW + msg + RESET])
            self.logger.log(msg)
            return True
        else:
            msg = f"ERROR OUT OF MEMORY: Proceso PID {pcb.pid} rechazado. Pide {pcb.size_mb} MB, disponible: {self.TOTAL_MEMORY - self.used_memory} MB."
            print_red_box([YELLOW + f"Intentando ingresar Proceso PID: {pcb.pid}" + RESET, YELLOW + msg + RESET])
            self.logger.log(msg)
            return False

    def free(self, pcb):
        self.used_memory -= pcb.size_mb
        msg = f"MEMORIA: Proceso PID {pcb.pid} liberó {pcb.size_mb} MB. Uso RAM: {self.used_memory}/{self.TOTAL_MEMORY} MB."
        print_red_box([YELLOW + msg + RESET])
        self.logger.log(msg)


class BinarySemaphore:
    def __init__(self, logger):
        self.value = 1
        self.waiting_queue = deque()
        self.logger = logger
        self.current_owner = None

    def wait(self, pcb):
        if self.value == 1:
            self.value = 0
            self.current_owner = pcb.pid
            msg = f"CONCURRENCIA: Proceso PID {pcb.pid} ejecutó wait() e INGRESÓ a la Sección Crítica."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return True
        else:
            pcb.state = "BLOQUEADO"
            self.waiting_queue.append(pcb)
            msg = f"CONCURRENCIA: Sección Crítica ocupada por PID {self.current_owner}. PID {pcb.pid} BLOQUEADO y enviado a cola del semáforo."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return False

    def signal(self):
        if self.waiting_queue:
            next_pcb = self.waiting_queue.popleft()
            next_pcb.state = "LISTO"
            self.current_owner = next_pcb.pid
            msg = f"CONCURRENCIA: Proceso PID {next_pcb.pid} DESBLOQUEADO de la cola y movido a la Cola de Listos."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return next_pcb
        else:
            self.value = 1
            self.current_owner = None
            msg = "CONCURRENCIA: Sección Crítica liberada exitosamente."
            print_red_box([YELLOW + msg + RESET])
            self.logger.log(msg)
            return None


class DeadlockManager:
    def __init__(self, logger):
        self.logger = logger
        self.resource1 = None
        self.resource2 = None
        self.is_deadlocked = False

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

    def resolve(self, victim_pid):
        if not self.is_deadlocked:
            print_red_box([YELLOW + "Deadlock: Actualmente no existe ninguna condición de interbloqueo activa." + RESET])
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
            print_red_box([YELLOW + "PID no válido para resolución. Use 101 o 102." + RESET])


class KernelSimulator:
    def __init__(self, quantum=3):
        self.quantum = quantum
        self.logger = EventLogger()
        self.memory = MemoryManager(self.logger)
        self.semaphore = BinarySemaphore(self.logger)
        self.deadlock_mgr = DeadlockManager(self.logger)
        self.ready_queue = deque()
        self.pid_counter = 1

    def create_process(self, size_mb, burst_time):
        pcb = PCB(self.pid_counter, size_mb, burst_time)
        if self.memory.allocate(pcb):
            self.ready_queue.append(pcb)
            self.logger.log(f"PROCESO: PID {pcb.pid} agregado a la Cola de Listos.")
            self.pid_counter += 1
            return pcb
        return None

    def run_round_robin(self):
        if not self.ready_queue:
            print_red_box([YELLOW + "[CPU] No hay procesos listos para ejecutar." + RESET])
            return

        print_red_box([YELLOW + f"EJECUTANDO PLANIFICADOR ROUND ROBIN (Quantum = {self.quantum}s)" + RESET])

        while self.ready_queue:
            current = self.ready_queue.popleft()
            current.state = "EJECUCION"
            
            exec_time = min(self.quantum, current.remaining_time)
            current.remaining_time -= exec_time

            if current.remaining_time > 0:
                current.state = "LISTO"
                self.ready_queue.append(current)
                msg = f"PLANIFICADOR: Quantum de {self.quantum}s agotado. Context Switch PID {current.pid}."
                print_red_box([YELLOW + f"CPU: Ejecutando PID {current.pid} por {exec_time}s..." + RESET, YELLOW + msg + RESET])
                self.logger.log(msg)
            else:
                current.state = "TERMINADO"
                msg = f"PLANIFICADOR: PID {current.pid} completó su ejecución."
                print_red_box([YELLOW + f"CPU: Ejecutando PID {current.pid} por {exec_time}s..." + RESET, YELLOW + msg + RESET])
                self.logger.log(msg)
                self.memory.free(current)


def main():
    kernel = KernelSimulator(quantum=3)

    while True:
        print()
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
                print_red_box([YELLOW + "Error: Ingrese números enteros válidos." + RESET])

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
                print_red_box([YELLOW + "Error: PID inválido." + RESET])

        elif opcion == "7":
            kernel.logger.show_logs()

        elif opcion == "8":
            print_red_box([YELLOW + "Cerrando el Simulador de Kernel..." + RESET])
            break
        else:
            print_red_box([YELLOW + "Opción no válida. Intente de nuevo." + RESET])

if __name__ == "__main__":
    main()