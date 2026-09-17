import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import "./styles.scss";
import "./notifications.scss";

createRoot(document.getElementById("root")!).render(<App />);
