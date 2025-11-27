import React from 'react';

function UnitGrid({ units, selectedUnit, onSelectUnit, loading }) {
    if (loading) {
        return <div className="loading">Loading units...</div>;
    }

    return (
        <div className="units-section">
            <h3>Units</h3>
            <div className="units-grid">
                {units.map(unit => (
                    <div
                        key={unit.unitId || unit.id}
                        className={`unit-card ${selectedUnit?.unitId === unit.unitId ? 'active' : ''}`}
                        onClick={() => onSelectUnit(unit)}
                    >
                        <h4>{unit.title || `Unit ${unit.unitId}`}</h4>
                        <p>{unit.description}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default UnitGrid;
