import numpy as np
import matplotlib.pyplot as plt
import time
import os

class OpenEcology:
    def __init__(self, n_nodes=64, state_dim=16):
        self.n_nodes = n_nodes
        self.state_dim = state_dim
        self.reset()

    def reset(self):
        # State vector
        self.X = np.random.normal(0, 0.1, (self.n_nodes, self.state_dim))
        self.X /= np.linalg.norm(self.X, axis=-1, keepdims=True) + 1e-8
        
        # Connectivity Matrix (W)
        self.W = np.random.uniform(0, 1.0, (self.n_nodes, self.n_nodes))
        self.W = (self.W < 0.1).astype(np.float32)
        np.fill_diagonal(self.W, 0.0)
        self.W /= self.W.sum(axis=-1, keepdims=True) + 1e-8
        
        self.M = np.zeros((self.n_nodes, self.state_dim))

    def step(self, dt=0.01, noise_sigma=0.05, coupling=0.1, pruning_threshold=0.0):
        # Difusión estándar simple
        deg = self.W.sum(axis=-1, keepdims=True)
        F_geo = (self.W @ self.X) - (deg * self.X)
        F_mem = self.M - self.X
        
        drift = coupling * F_geo + 0.05 * F_mem
        noise = noise_sigma * np.random.normal(0, 1.0, self.X.shape)
        
        self.X = self.X + drift * dt + noise * np.sqrt(dt)
        self.X /= np.linalg.norm(self.X, axis=-1, keepdims=True) + 1e-8
        
        # Similitud
        sim = self.X @ self.X.T
        
        # Heurística para evitar el estancamiento: Repulsión por sobresimilitud
        # Si dos nodos son casi idénticos, comienzan a repelerse para mantener la diversidad del sistema
        sim = np.where(sim > 0.85, -0.5, sim)
        sim = np.maximum(sim, -0.2) # Permitimos valores negativos para romper enlaces
        np.fill_diagonal(sim, 0.0)
        
        # Actualización de matriz con penalización para mantener dinamismo continuo
        self.W = 0.98 * self.W + 0.02 * sim
        self.W = np.maximum(self.W, 0.0) # Evitamos pesos negativos
        
        if pruning_threshold > 0.0:
            self.W[self.W < pruning_threshold] = 0.0
            
        self.W /= self.W.sum(axis=-1, keepdims=True) + 1e-8
        self.M = 0.95 * self.M + 0.05 * self.X

    def apply_shock(self, magnitude=0.5):
        """Inyecta ruido masivo para desestabilizar la red."""
        self.X += np.random.normal(0, magnitude, self.X.shape)
        self.X /= np.linalg.norm(self.X, axis=-1, keepdims=True) + 1e-8

    def polarize(self):
        """Fuerza a los nodos a separarse en dos grupos opuestos."""
        half = self.n_nodes // 2
        self.X[:half] += 0.5
        self.X[half:] -= 0.5
        self.X /= np.linalg.norm(self.X, axis=-1, keepdims=True) + 1e-8
        
    def shatter_topology(self):
        """Destruye el 80% de las conexiones para forzar reestructuración."""
        mask = np.random.rand(*self.W.shape) > 0.8
        self.W *= mask
        self.W /= self.W.sum(axis=-1, keepdims=True) + 1e-8

def render_terminal(W, step, coherence, steps, event_msg, trajectory_val):
    """Monitor avanzado con telemetría, matriz y trayectoria lineal."""
    size = 20
    indices = np.linspace(0, W.shape[0] - 1, size).astype(int)
    small_w = W[np.ix_(indices, indices)]
    
    chars = [" ", "░", "▒", "▓", "█"]
    
    print("\033[H\033[J")
    print(f"┏━━━━ PRA-X ADVANCED MONITOR ━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print(f"┃ Paso: {step:3d} / {steps} | Coherencia: {coherence:.6f}       ┃")
    
    # Barra de Coherencia
    bar_w = 20
    filled = int(min(coherence * 2000, bar_w))
    bar = "█" * filled + "░" * (bar_w - filled)
    
    # Visualización de Trayectoria (Simplificada a 1D)
    traj_w = 20
    t_pos = int(((trajectory_val + 1) / 2) * traj_w)
    t_pos = max(0, min(traj_w - 1, t_pos))
    traj_line = "—" * t_pos + "●" + "—" * (traj_w - t_pos - 1)

    print(f"┃ COH: [{bar}] | TRAJ: [{traj_line}] ┃")
    print(f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫")
    
    for row in small_w:
        line = "┃ "
        for val in row:
            idx = int(min(val * 50, 4))
            line += chars[idx] * 2
        line += " ┃"
        print(line)
    print(f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print(f"\n>> EVENTO: {event_msg}")
    print(f"   • Estabilidad: {1.0 - (1.0/(1.0+coherence)):.4f}")
    print(f"   • Densidad de Red: {np.mean(W > 0.005):.2%}")
    print(f"   • Nota: Ejecución ralentizada para observación.")

def run_simulation(steps=600):
    eco = OpenEcology()
    coherence_history = []
    trajectory_history = []
    
    print("\033[?25l")
    
    try:
        for i in range(steps):
            event = "Normalización dinámica"
            coupling = 0.1
            pruning = 0.0
            
            # Programación de Shocks y Eventos
            if 100 <= i < 120:
                eco.apply_shock(0.3)
                event = "SHOCK: Inyección de ruido exógeno"
            elif i == 200:
                eco.polarize()
                event = "CRÍTICO: Polarización de estados inducida"
            elif 250 <= i < 300:
                coupling = 0.8
                pruning = 0.005
                event = "ACELERACIÓN: Centralización y Poda Sináptica"
            elif i == 400:
                eco.shatter_topology()
                event = "COLAPSO ESTRUCTURAL: Destrucción de Topología"
            elif 401 <= i < 450:
                event = "RECUPERACIÓN: Reconstrucción Rizomática"
                pruning = 0.008 # Fuerte poda para crear clústeres claros
            else:
                pruning = 0.002 # Poda base para evitar saturación
            
            eco.step(coupling=coupling, pruning_threshold=pruning)
            
            # Calculamos coherencia
            sim = eco.X @ eco.X.T
            mean_coh = np.mean(eco.W * sim)
            coherence_history.append(mean_coh)
            
            # Trayectoria: promedio del primer componente del estado
            traj_val = np.mean(eco.X[:, 0])
            trajectory_history.append(traj_val)
            
            if i % 2 == 0:
                render_terminal(eco.W, i, mean_coh, steps, event, traj_val)
                time.sleep(0.06) # Ralentizado deliberadamente
                
        print("\nSimulación finalizada.")
        
        # Plot final bimodal
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        ax1.plot(coherence_history, color="#3b82f6", lw=2)
        ax1.set_title("Evolución de Coherencia")
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(trajectory_history, color="#10b981", lw=2)
        ax2.set_title("Trayectoria del Sistema (Fase)")
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig("simulation_results.png", dpi=120)
        print("Resultados bimodales guardados en simulation_results.png")
        
    finally:
        print("\033[?25h")

if __name__ == "__main__":
    run_simulation()
