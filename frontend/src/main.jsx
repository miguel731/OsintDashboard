import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {}
  render() {
    if (this.state.hasError) {
      return React.createElement(
        "div",
        { style: { padding: 16, fontFamily: "system-ui" } },
        "Ocurrió un error en la UI. Reconstruye el frontend con Docker para actualizar el build."
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  React.createElement(ErrorBoundary, null, React.createElement(App))
);