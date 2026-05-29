import numpy as np
import matplotlib.pyplot as plt
import time
import os

class ToyDynamics:
    """
    Simulador conceptual abstracto para demostracion educativa de sistemas dinamicos.
    Utiliza una dinamica simple de consenso de opinion y flocado (flocking) en red.
    """
    def __init__(self, n_nodes=32, state_dim=8):
        self.n_nodes = n_nodes
        self.state_dim = state_dim
        
        # Alerta de escala para N > 50 (cuello de botella de CPU y bucles interpretados)
        if self.n_nodes > 50:
            print("\033[93m" + "="*80)
            print("[AVISO DE ESCALA] Simulación local en CPU sin aceleración nativa.")
            print("Para grafos de alta densidad (N > 50) y acoplamiento multiescala real,")
            print("se requiere el motor compilado en Rust/JAX de producción de PRA-X.")
            print("="*80 + "\033[0m")
            time.sleep(2)
            
        self.reset()

    def reset(self):
        # Estados abstractos de los nodos (posiciones en la esfera unitaria)
        self.states = np.random.normal(0, 1.0, (self.n_nodes, self.state_dim))
        for i in range(self.n_nodes):
            norm = np.linalg.norm(self.states[i]) + 1e-8
            self.states[i] /= norm
            
        # Matriz de influencia (W) inicializada aleatoriamente
        self.weights = np.random.uniform(0.1, 1.0, (self.n_nodes, self.n_nodes))
        for i in range(self.n_nodes):
            self.weights[i, i] = 0.0
            row_sum = self.weights[i].sum() + 1e-8
            self.weights[i] /= row_sum
            
        # Atractor estático de referencia (objetivo común abstracto)
        self.target_attractor = np.random.normal(0, 1.0, (self.state_dim,))
        self.target_attractor /= np.linalg.norm(self.target_attractor) + 1e-8
        
        # Energía del sistema (variable escalar homeostática)
        self.energy = 100.0

    def step(self, alpha=0.1, noise_sigma=0.04):
        """
        Paso de integracion temporal de juguete.
        Actualiza los pesos usando bucles explicitos anidados en Python para simular
        de manera deliberada el costo de ejecucion en CPU sin el motor de Rust.
        """
        n = self.n_nodes
        d = self.state_dim
        
        # 1. Actualizacion de la matriz de influencia (Bucle O(N^2 * D) en Python puro)
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Calculo manual de distancia euclidiana (deliberadamente ineficiente)
                    dist = 0.0
                    for k in range(d):
                        diff = self.states[i, k] - self.states[j, k]
                        dist += diff * diff
                    dist = dist ** 0.5
                    
                    # Regla de atraccion por proximidad de juguete
                    self.weights[i, j] = 0.96 * self.weights[i, j] + 0.04 / (1.0 + dist)
                else:
                    self.weights[i, j] = 0.0
                    
        # Normalizacion manual de filas
        for i in range(n):
            row_sum = 0.0
            for j in range(n):
                row_sum += self.weights[i, j]
            row_sum += 1e-8
            for j in range(n):
                self.weights[i, j] /= row_sum

        # 2. Actualizacion de los estados de los nodos (Consenso + Atractor + Ruido)
        new_states = np.zeros_like(self.states)
        energy_factor = self.energy / 100.0
        
        for i in range(n):
            # Consenso: promedio ponderado de los estados vecinos
            neighbor_sum = np.zeros(d)
            for j in range(n):
                weight = self.weights[i, j]
                for k in range(d):
                    neighbor_sum[k] += weight * self.states[j, k]
            
            # Dinamica: deriva hacia los vecinos y hacia el atractor estatico
            for k in range(d):
                drift = alpha * (neighbor_sum[k] - self.states[i, k]) + 0.03 * energy_factor * (self.target_attractor[k] - self.states[i, k])
                noise = noise_sigma * np.random.normal(0, 1.0)
                new_states[i, k] = self.states[i, k] + drift + noise
                
        # Normalizar estados proyectando a la esfera unitaria
        for i in range(n):
            norm = 0.0
            for k in range(d):
                norm += new_states[i, k] * new_states[i, k]
            norm = norm ** 0.5 + 1e-8
            for k in range(d):
                new_states[i, k] /= norm
                
        self.states = new_states
        
        # Decaimiento natural de la energia
        self.energy = max(10.0, self.energy - 0.08)

    def apply_shock(self, magnitude=0.4):
        """Inyeccion de ruido exogeno. Restablece la energia del sistema."""
        self.states += np.random.normal(0, magnitude, self.states.shape)
        for i in range(self.n_nodes):
            norm = np.linalg.norm(self.states[i]) + 1e-8
            self.states[i] /= norm
        self.energy = min(100.0, self.energy + 40.0)

    def polarize(self):
        """Genera una division binaria forzando a dos subgrupos a orientaciones opuestas."""
        half = self.n_nodes // 2
        self.states[:half] += 0.8
        self.states[half:] -= 0.8
        for i in range(self.n_nodes):
            norm = np.linalg.norm(self.states[i]) + 1e-8
            self.states[i] /= norm

    def shatter_topology(self):
        """Introduce desconexion masiva en la matriz de pesos."""
        mask = np.random.rand(*self.weights.shape) > 0.75
        self.weights *= mask
        for i in range(self.n_nodes):
            row_sum = self.weights[i].sum() + 1e-8
            self.weights[i] /= row_sum

def render_terminal(W, step, coherence, steps, event_msg, energy):
    """Monitor simplificado de juguete para la visualizacion ASCII en terminal."""
    size = 20
    indices = np.linspace(0, W.shape[0] - 1, size).astype(int)
    small_w = W[np.ix_(indices, indices)]
    
    chars = [" ", "░", "▒", "▓", "█"]
    
    print("\033[H\033[J")
    print(f"┏━━━━ PRA-X TOY SANDBOX MONITOR ━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print(f"┃ Paso: {step:3d} / {steps} | Coherencia: {coherence:.6f}       ┃")
    
    # Barra de Coherencia
    bar_w = 20
    filled = int(min(coherence * 2000, bar_w))
    bar = "█" * filled + "░" * (bar_w - filled)
    
    # Barra de Energia
    energy_w = 15
    e_filled = int((energy / 100.0) * energy_w)
    e_bar = "⚡" * (e_filled // 2) + "░" * (energy_w - e_filled)
    e_bar = e_bar[:energy_w]

    print(f"┃ COH: [{bar}] | ENERGIA: [{e_bar}] ┃")
    print(f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫")
    
    for row in small_w:
        line = "┃ "
        for val in row:
            idx = int(min(val * 40, 4))
            line += chars[idx] * 2
        line += " ┃"
        print(line)
    print(f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print(f"\n>> EVENTO EN CURSO: {event_msg}")
    print(f"   • Consenso Ficticio: {coherence * 100:.2f}%")
    print(f"   • Densidad de Enlaces: {np.mean(W > 0.01):.2%}")
    print(f"   • Nota: Ejecución en CPU simulada.")

def run_simulation(steps=500):
    eco = ToyDynamics(n_nodes=40, state_dim=8)
    coherence_history = []
    energy_history = []
    
    print("\033[?25l")
    
    try:
        for i in range(steps):
            event = "Evolución inercial"
            alpha = 0.08
            
            # Programacion de eventos artificiales para dinamica visual
            if 100 <= i < 115:
                eco.apply_shock(0.25)
                event = "SHOCK: Ruido externo aplicado"
            elif i == 200:
                eco.polarize()
                event = "BIFURCACIÓN: Polarización forzada"
            elif 260 <= i < 290:
                alpha = 0.25
                event = "ACELERACIÓN: Atracción de campo intensa"
            elif i == 380:
                eco.shatter_topology()
                event = "RUPTURA: Disrupción de enlaces topológicos"
            
            eco.step(alpha=alpha)
            
            # Coherencia simplificada: promedio de correlaciones
            sim = eco.states @ eco.states.T
            mean_coh = float(np.mean(eco.weights * sim))
            coherence_history.append(mean_coh)
            energy_history.append(eco.energy)
            
            if i % 3 == 0:
                render_terminal(eco.weights, i, mean_coh, steps, event, eco.energy)
                time.sleep(0.05)
                
        print("\nSimulación finalizada.")
        
        # Grafico simple bimodal para guardar resultados
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        ax1.plot(coherence_history, color="#a855f7", lw=2)
        ax1.set_title("Evolución de Coherencia Ficticia")
        ax1.set_xlabel("Paso")
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(energy_history, color="#ec4899", lw=2)
        ax2.set_title("Evolución de Energía Decadente")
        ax2.set_xlabel("Paso")
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig("simulation_results.png", dpi=100)
        print("Resultados de juguete guardados en simulation_results.png")
        
    finally:
        print("\033[?25h")

if __name__ == "__main__":
    run_simulation()
