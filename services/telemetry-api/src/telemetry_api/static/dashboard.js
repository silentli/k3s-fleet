const stations = [
  { id: "Charging_Dock", name: "Charging Dock", x: 0, y: 0, dock: true },
  { id: "Assembly_Line_A", name: "Assembly A", x: 80, y: 20 },
  { id: "Assembly_Line_B", name: "Assembly B", x: 80, y: 60 },
  { id: "Warehouse_Pick", name: "Warehouse", x: 10, y: 90 },
  { id: "Quality_Control", name: "Quality Control", x: 40, y: 50 },
];

const svgNamespace = "http://www.w3.org/2000/svg";
const stationsLayer = document.getElementById("stations");
const robotsLayer = document.getElementById("robots");
const robotList = document.getElementById("robot-list");
const connectionStatus = document.getElementById("connection-status");

function floorY(y) {
  return 100 - y;
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNamespace, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function drawStations() {
  stations.forEach((station) => {
    // Stations can sit at the floor edge (the dock is at 0, 0). Keep their
    // marker inside the visual boundary without changing their real position.
    const x = clamp(station.x, 5, 95);
    const y = clamp(floorY(station.y), 5, 95);
    const group = svgElement("g", { class: `station${station.dock ? " dock" : ""}` });
    group.append(svgElement("rect", { x: x - 4, y: y - 4, width: 8, height: 8, rx: 1 }));
    const label = svgElement("text", {
      x: station.dock ? 8 : x,
      y: y > 90 ? y - 6 : y + 7,
      "text-anchor": station.dock ? "start" : "middle",
    });
    label.textContent = station.name;
    group.append(label);
    stationsLayer.append(group);
  });
}

function drawRobots(robots) {
  robotsLayer.replaceChildren();
  robots.forEach((robot) => {
    const y = floorY(robot.y);
    const group = svgElement("g", { transform: `translate(${robot.x} ${y})` });
    group.append(svgElement("circle", { class: "robot-marker", cx: 0, cy: 0, r: 3.4 }));
    const radians = (robot.heading_deg || 0) * (Math.PI / 180);
    group.append(svgElement("line", {
      class: "robot-heading",
      x1: 0,
      y1: 0,
      x2: Math.cos(radians) * 2.2,
      y2: -Math.sin(radians) * 2.2,
    }));
    const labelIsNearLeftEdge = robot.x < 20;
    const labelIsNearRightEdge = robot.x > 80;
    const label = svgElement("text", {
      class: "robot-label",
      x: labelIsNearLeftEdge ? 5 : labelIsNearRightEdge ? -5 : 0,
      y: y < 12 ? 6 : -5,
      "text-anchor": labelIsNearLeftEdge ? "start" : labelIsNearRightEdge ? "end" : "middle",
    });
    label.textContent = `robot-${robot.device_id.split("-").at(-1)}`;
    group.append(label);
    robotsLayer.append(group);
  });
}

function destinationLabel(destinationId) {
  return stations.find((station) => station.id === destinationId)?.name ?? destinationId.replaceAll("_", " ");
}

function renderRobotList(robots) {
  robotList.replaceChildren();
  if (!robots.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Waiting for robot telemetry…";
    robotList.append(empty);
    return;
  }

  robots.forEach((robot) => {
    const card = document.createElement("article");
    card.className = "robot-card";
    const name = document.createElement("p");
    name.className = "robot-card__name";
    name.textContent = robot.device_id;
    const details = document.createElement("div");
    details.className = "robot-card__details";
    const status = document.createElement("span");
    status.className = "status";
    status.textContent = robot.status;
    const battery = document.createElement("span");
    battery.textContent = `${robot.battery_soc_pct}% battery`;
    const summary = document.createElement("div");
    summary.className = "robot-card__summary";
    summary.append(status, battery);

    const destinationLabelElement = document.createElement("span");
    destinationLabelElement.className = "robot-card__label";
    destinationLabelElement.textContent = "Destination: ";
    const destination = document.createElement("span");
    destination.className = "robot-card__value";
    destination.textContent = destinationLabel(robot.destination);
    const destinationRow = document.createElement("p");
    destinationRow.className = "robot-card__row";
    destinationRow.append(destinationLabelElement, destination);

    const positionLabel = document.createElement("span");
    positionLabel.className = "robot-card__label";
    positionLabel.textContent = "Position: ";
    const position = document.createElement("span");
    position.className = "robot-card__value";
    position.textContent = `${robot.x.toFixed(1)}, ${robot.y.toFixed(1)}`;
    const positionRow = document.createElement("p");
    positionRow.className = "robot-card__row";
    positionRow.append(positionLabel, position);
    details.append(summary, destinationRow, positionRow);
    card.append(name, details);
    robotList.append(card);
  });
}

async function refreshRobots() {
  try {
    const response = await fetch("/robots");
    if (!response.ok) throw new Error("The API did not return robot data.");
    const robots = await response.json();
    drawRobots(robots);
    renderRobotList(robots);
    connectionStatus.textContent = `${robots.length} robot${robots.length === 1 ? "" : "s"} online`;
  } catch (error) {
    connectionStatus.textContent = "Unable to load robot data";
    robotList.innerHTML = '<p class="empty">The dashboard will retry automatically.</p>';
  }
}

drawStations();
refreshRobots();
setInterval(refreshRobots, 5000);
