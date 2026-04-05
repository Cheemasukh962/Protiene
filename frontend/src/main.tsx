import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { DemoDayProvider } from "./context/DemoDayContext";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <DemoDayProvider>
          <App />
        </DemoDayProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
