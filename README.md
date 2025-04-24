# Adaptive-Traffic-Light


---

## 📁 Folder structure


## 🛠 Installation & Preparation
### Installation
1. Install SUMO: [Download](https://eclipse.dev/sumo/)
2. Install required library in python:
```bash
pip install numpy
pip install pandas
pip install matplotlib
pip install sumolib traci
```

### How to use
1. **SUMO Simulation**

Generate network
```bash
cd ./network
netconvert -n simple.nod.xml -e simple.edg.xml -o simple.net.xml
```
Generate Vehicle Routes
```bash
cd ./SUMO/scripts
python -u generate_vehicle.py
```
2. **AI model**

Train the Model and Export Weights
```bash
cd model
python model.py
```