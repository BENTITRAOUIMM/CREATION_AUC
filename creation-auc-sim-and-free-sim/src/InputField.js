// src/InputField.js
import React from 'react';

function InputField({ type, placeholder, value, onChange }) {
  return (
    <input
      type={type}
      className="form-control mb-3 short-input"
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      required
    />
  );
}

export default InputField;
